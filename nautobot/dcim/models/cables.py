import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import classproperty

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models.fields import ColorField
from nautobot.core.utils.data import to_meters
from nautobot.dcim.choices import CableLengthUnitChoices, CableTypeChoices
from nautobot.extras.models import Status, StatusField
from nautobot.extras.utils import extras_features

# TODO: There's an ugly circular-import pattern where if we move this import "up" to above, we get into an import loop
# from dcim.models.cables to core.models.generics to extras.models.datasources to core.models.generics.
# Deferring the update to here works for now; fixing so that core.models.generics doesn't depend on extras.models
# would be the much more invasive but much more "correct" fix.
from nautobot.core.models.generics import BaseModel, PrimaryModel  # isort: skip

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

    Terminations are managed through the CableEnd model, which enables
    multiple terminations per cable side.
    """

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

    natural_key_field_names = ["pk"]

    class Meta:
        ordering = ["pk"]

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

        # Validate length and length_unit
        if self.length is not None and not self.length_unit:
            raise ValidationError("Must specify a unit when setting a cable length")
        elif self.length is None:
            self.length_unit = ""

        # Note: Most cable validation is now handled by CableEnd.clean()
        # The following validations are handled elsewhere:
        # - Termination existence: Validated by ForeignKey constraint on CableEnd
        # - Termination already cabled: Validated in CableEnd.clean()
        # - Interface types (NONCONNECTABLE_IFACE_TYPES): Validated in CableEnd.clean()
        # - CircuitTermination provider network: Validated in CableEnd.clean()
        # - Termination immutability: Should be enforced in forms/views
        # - Compatible termination types: Should be validated in forms when creating cable with both sides
        # - RearPort position matching: Should be validated in forms
        # - Self-connection prevention: Should be validated in forms
        # - FrontPort/RearPort correspondence: Should be validated in forms

    def save(self, *args, **kwargs):
        # Store the given length (if any) in meters for use in database ordering
        if self.length and self.length_unit:
            self._abs_length = to_meters(self.length, self.length_unit)
        else:
            self._abs_length = None

        super().save(*args, **kwargs)

        # Update the private pk used in __str__ in case this is a new object (i.e. just got its pk)
        self._pk = self.pk



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
            ("cable_termination",),  # Each termination can only be connected once
        ]

    def __str__(self):
        return f"{self.cable} - side {self.cable_side} - position {self.position}"

    def clean(self):
        super().clean()

        # Note: Duplicate cable connections are prevented by unique_together constraint on cable_termination
        # The database will raise IntegrityError if a termination is already cabled

        if self.cable_termination:
            # Import here to avoid circular imports
            from nautobot.circuits.models import CircuitTermination
            from nautobot.dcim.constants import NONCONNECTABLE_IFACE_TYPES
            from nautobot.dcim.models import Interface

            # Validate interface types for non-connectable interfaces
            if isinstance(self.cable_termination, Interface):
                if self.cable_termination.type in NONCONNECTABLE_IFACE_TYPES:
                    raise ValidationError(
                        f"Cables cannot be terminated to {self.cable_termination.get_type_display()} interfaces"
                    )

            # Validate CircuitTermination provider network restriction
            if isinstance(self.cable_termination, CircuitTermination):
                if self.cable_termination.provider_network is not None:
                    raise ValidationError("Circuit terminations attached to a provider network may not be cabled.")
