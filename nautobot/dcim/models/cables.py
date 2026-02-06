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

    def _get_termination(self, side):
        """Return the CableTermination on the given side (a or b) via CableEnd."""
        # Check for a pending (not yet saved) termination set via the setter
        pending = getattr(self, f"_pending_termination_{side}", None)
        if pending is not None:
            return pending
        # Otherwise look it up from the database
        if self.present_in_database:
            for cable_end in self.cable_ends.all():
                if cable_end.cable_side == side:
                    return cable_end.cable_termination
        return None

    def _set_termination(self, side, value):
        """Store a termination to be saved as a CableEnd via the post_save signal."""
        setattr(self, f"_pending_termination_{side}", value)

    @property
    def termination_a(self):
        """Backwards-compatible access to the side A termination via CableEnd."""
        return self._get_termination("a")

    @termination_a.setter
    def termination_a(self, value):
        self._set_termination("a", value)

    @property
    def termination_b(self):
        """Backwards-compatible access to the side B termination via CableEnd."""
        return self._get_termination("b")

    @termination_b.setter
    def termination_b(self, value):
        self._set_termination("b", value)

    @property
    def termination_a_type(self):
        """Backwards-compatible access to the side A termination content type."""
        from django.contrib.contenttypes.models import ContentType

        term = self.termination_a
        if term is not None:
            return ContentType.objects.get_for_model(term)
        return None

    @termination_a_type.setter
    def termination_a_type(self, value):
        # Stored but not directly used - termination type is derived from the termination object
        self._pending_termination_a_type = value

    @property
    def termination_b_type(self):
        """Backwards-compatible access to the side B termination content type."""
        from django.contrib.contenttypes.models import ContentType

        term = self.termination_b
        if term is not None:
            return ContentType.objects.get_for_model(term)
        return None

    @termination_b_type.setter
    def termination_b_type(self, value):
        # Stored but not directly used - termination type is derived from the termination object
        self._pending_termination_b_type = value

    @property
    def termination_a_id(self):
        """Backwards-compatible access to the side A termination ID."""
        term = self.termination_a
        return term.pk if term is not None else None

    @property
    def termination_b_id(self):
        """Backwards-compatible access to the side B termination ID."""
        term = self.termination_b
        return term.pk if term is not None else None

    def clean(self):
        super().clean()

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

        super().save(*args, **kwargs)

        # Update the private pk used in __str__ in case this is a new object (i.e. just got its pk)
        self._pk = self.pk

        # Create CableEnd records for any pending terminations set via the property setters
        # (e.g. cable.termination_a = interface; cable.save())
        for side in ("a", "b"):
            pending = getattr(self, f"_pending_termination_{side}", None)
            if pending is not None:
                CableEnd.objects.get_or_create(
                    cable=self,
                    cable_termination=pending,
                    cable_side=side,
                    defaults={"position": 0},
                )
                setattr(self, f"_pending_termination_{side}", None)



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
