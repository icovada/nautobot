import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils.functional import classproperty

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.fields import ColorField
from nautobot.core.utils.data import to_meters
from nautobot.dcim.choices import CableLengthUnitChoices, CableTypeChoices
from nautobot.dcim.constants import CABLE_TERMINATION_MODELS, COMPATIBLE_TERMINATION_TYPES, NONCONNECTABLE_IFACE_TYPES
from nautobot.extras.models import Status, StatusField
from nautobot.extras.utils import extras_features

# TODO: There's an ugly circular-import pattern where if we move this import "up" to above, we get into an import loop
# from dcim.models.cables to core.models.generics to extras.models.datasources to core.models.generics.
# Deferring the update to here works for now; fixing so that core.models.generics doesn't depend on extras.models
# would be the much more invasive but much more "correct" fix.
from nautobot.core.models.generics import BaseModel, PrimaryModel  # isort: skip

from .device_components import RearPort
from .devices import Device

__all__ = (
    "Cable",
    "CableEnd",
)

logger = logging.getLogger(__name__)


#
# Cables
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class Cable(PrimaryModel):
    """
    A physical connection between two endpoints.
    """

    termination_a_type = models.ForeignKey(
        to=ContentType,
        limit_choices_to=CABLE_TERMINATION_MODELS,
        on_delete=models.PROTECT,
        related_name="+",
    )
    termination_a_id = models.UUIDField()
    termination_a = GenericForeignKey(ct_field="termination_a_type", fk_field="termination_a_id")
    termination_b_type = models.ForeignKey(
        to=ContentType,
        limit_choices_to=CABLE_TERMINATION_MODELS,
        on_delete=models.PROTECT,
        related_name="+",
    )
    termination_b_id = models.UUIDField()
    termination_b = GenericForeignKey(ct_field="termination_b_type", fk_field="termination_b_id")
    type = models.CharField(max_length=50, choices=CableTypeChoices, blank=True)
    status = StatusField(blank=False, null=False)
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    color = ColorField(blank=True)
    length = models.PositiveSmallIntegerField(blank=True, null=True)
    length_unit = models.CharField(
        max_length=50,
        choices=CableLengthUnitChoices,
        blank=True,
    )
    # Stores the normalized length (in meters) for database ordering
    _abs_length = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    # Cache the associated device (where applicable) for the A and B terminations. This enables filtering of Cables by
    # their associated Devices.
    _termination_a_device = models.ForeignKey(
        to=Device, on_delete=models.CASCADE, related_name="+", blank=True, null=True
    )
    _termination_b_device = models.ForeignKey(
        to=Device, on_delete=models.CASCADE, related_name="+", blank=True, null=True
    )

    natural_key_field_names = ["pk"]

    class Meta:
        ordering = [
            "termination_a_type",
            "termination_a_id",
            "termination_b_type",
            "termination_b_id",
        ]
        unique_together = (
            ("termination_a_type", "termination_a_id"),
            ("termination_b_type", "termination_b_id"),
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # A copy of the PK to be used by __str__ in case the object is deleted
        self._pk = self.pk

        if self.present_in_database:
            # Cache the original status so we can check later if it's been changed
            self._orig_status = self.status
        else:
            self._orig_status = None

    def __str__(self):
        pk = self.pk or self._pk
        return self.label or f"#{pk}"

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def STATUS_CONNECTED(cls):  # pylint: disable=no-self-argument
        """Return a cached "connected" `Status` object for later reference."""
        if getattr(cls, "__status_connected", None) is None:
            try:
                cls.__status_connected = Status.objects.get_for_model(Cable).get(name="Connected")
            except Status.DoesNotExist:
                logger.warning("Status 'connected' not found for dcim.cable")
                return None

        return cls.__status_connected

    def clean(self):
        super().clean()

        # We import this in this method due to circular importing issues.
        from nautobot.circuits.models import CircuitTermination

        # Validate that termination A exists
        if not hasattr(self, "termination_a_type"):
            raise ValidationError("Termination A type has not been specified")
        try:
            self.termination_a_type.model_class().objects.get(pk=self.termination_a_id)
        except ObjectDoesNotExist:
            raise ValidationError({"termination_a": f"Invalid ID for type {self.termination_a_type}"})

        # Validate that termination B exists
        if not hasattr(self, "termination_b_type"):
            raise ValidationError("Termination B type has not been specified")
        try:
            self.termination_b_type.model_class().objects.get(pk=self.termination_b_id)
        except ObjectDoesNotExist:
            raise ValidationError({"termination_b": f"Invalid ID for type {self.termination_b_type}"})

        # If editing an existing Cable instance, check that neither termination has been modified.
        if self.present_in_database:
            err_msg = "Cable termination points may not be modified. Delete and recreate the cable instead."

            existing_obj = Cable.objects.get(pk=self.pk)

            if (
                self.termination_a_type_id != existing_obj.termination_a_type_id
                or self.termination_a_id != existing_obj.termination_a_id
            ):
                raise ValidationError({"termination_a": err_msg})
            if (
                self.termination_b_type_id != existing_obj.termination_b_type_id
                or self.termination_b_id != existing_obj.termination_b_id
            ):
                raise ValidationError({"termination_b": err_msg})

        type_a = self.termination_a_type.model
        type_b = self.termination_b_type.model

        # Validate interface types
        if type_a == "interface" and self.termination_a.type in NONCONNECTABLE_IFACE_TYPES:
            raise ValidationError(
                {
                    "termination_a_id": f"Cables cannot be terminated to {self.termination_a.get_type_display()} interfaces"
                }
            )
        if type_b == "interface" and self.termination_b.type in NONCONNECTABLE_IFACE_TYPES:
            raise ValidationError(
                {
                    "termination_b_id": f"Cables cannot be terminated to {self.termination_b.get_type_display()} interfaces"
                }
            )

        # Check that termination types are compatible
        if type_b not in COMPATIBLE_TERMINATION_TYPES.get(type_a):
            raise ValidationError(
                f"Incompatible termination types: {self.termination_a_type} and {self.termination_b_type}"
            )

        # Check that two connected RearPorts have the same number of positions (if both are >1)
        if isinstance(self.termination_a, RearPort) and isinstance(self.termination_b, RearPort):
            if self.termination_a.positions > 1 and self.termination_b.positions > 1:
                if self.termination_a.positions != self.termination_b.positions:
                    raise ValidationError(
                        f"{self.termination_a} has {self.termination_a.positions} position(s) but "
                        f"{self.termination_b} has {self.termination_b.positions}. "
                        f"Both terminations must have the same number of positions (if greater than one)."
                    )

        # A termination point cannot be connected to itself
        if self.termination_a == self.termination_b:
            raise ValidationError(f"Cannot connect {self.termination_a_type} to itself")

        # A front port cannot be connected to its corresponding rear port
        if (
            type_a in ["frontport", "rearport"]
            and type_b in ["frontport", "rearport"]
            and (
                getattr(self.termination_a, "rear_port", None) == self.termination_b
                or getattr(self.termination_b, "rear_port", None) == self.termination_a
            )
        ):
            raise ValidationError("A front port cannot be connected to it corresponding rear port")

        # A CircuitTermination attached to a Provider Network cannot have a Cable
        if isinstance(self.termination_a, CircuitTermination) and self.termination_a.provider_network is not None:
            raise ValidationError(
                {"termination_a_id": "Circuit terminations attached to a provider network may not be cabled."}
            )
        if isinstance(self.termination_b, CircuitTermination) and self.termination_b.provider_network is not None:
            raise ValidationError(
                {"termination_b_id": "Circuit terminations attached to a provider network may not be cabled."}
            )

        # Check for an existing Cable connected to either termination object
        if self.termination_a.cable not in (None, self):
            raise ValidationError(f"{self.termination_a} already has a cable attached (#{self.termination_a.cable_id})")
        if self.termination_b.cable not in (None, self):
            raise ValidationError(f"{self.termination_b} already has a cable attached (#{self.termination_b.cable_id})")

        # Validate length and length_unit
        if self.length is not None and not self.length_unit:
            raise ValidationError("Must specify a unit when setting a cable length")
        elif self.length is None:
            self.length_unit = ""

    def save(self, *args, **kwargs):
        # Store the given length (if any) in meters for use in database ordering
        if self.length and self.length_unit:
            self._abs_length = to_meters(self.length, self.length_unit)
        else:
            self._abs_length = None

        # Store the parent Device for the A and B terminations (if applicable) to enable filtering
        if hasattr(self.termination_a, "device"):
            self._termination_a_device = self.termination_a.device
        if (
            not self._termination_a_device
            and hasattr(self.termination_a, "module")
            and self.termination_a.module.device
        ):
            self._termination_a_device = self.termination_a.module.device
        if hasattr(self.termination_b, "device"):
            self._termination_b_device = self.termination_b.device
        if (
            not self._termination_b_device
            and hasattr(self.termination_b, "module")
            and self.termination_b.module.device
        ):
            self._termination_b_device = self.termination_b.module.device

        super().save(*args, **kwargs)

        # Update the private pk used in __str__ in case this is a new object (i.e. just got its pk)
        self._pk = self.pk

    def get_compatible_types(self):
        """
        Return all termination types compatible with termination A.
        """
        if self.termination_a is None:
            return None
        return COMPATIBLE_TERMINATION_TYPES[self.termination_a._meta.model_name]


@extras_features("graphql")
class CableEnd(BaseModel):
    """
    A single termination point on a cable. Cables can have multiple terminations on each side (A and B).

    This model enables multi-cable terminations while maintaining backwards compatibility with the
    legacy Cable.termination_a/b fields.
    """

    class CableSide(models.TextChoices):
        A = "a", "A"
        B = "b", "B"

    cable = models.ForeignKey(
        to="Cable",
        on_delete=models.CASCADE,
        related_name="cable_ends",
    )
    cable_termination = models.ForeignKey(
        to="CableTermination",
        on_delete=models.CASCADE,
        related_name="cable_ends",
    )
    cable_side = models.CharField(max_length=1, choices=CableSide.choices)
    position = models.PositiveIntegerField(default=0)

    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ["cable", "cable_side", "position"]
        unique_together = [
            ("cable", "position", "cable_side"),
            ("cable_termination",),  # Each termination can only be connected once
        ]

    def __str__(self):
        return f"{self.cable} - side {self.cable_side} - position {self.position}"
