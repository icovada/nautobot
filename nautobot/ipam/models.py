import logging
import operator

import netaddr
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.functional import cached_property, classproperty

from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import AutoSlugField, JSONArrayField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.utils import array_to_string
from nautobot.core.utils.data import UtilizationData
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import RoleModelMixin, Status, StatusModel
from nautobot.extras.utils import extras_features
from nautobot.ipam import choices
from nautobot.virtualization.models import VirtualMachine, VMInterface
from .constants import (
    SERVICE_PORT_MAX,
    SERVICE_PORT_MIN,
    VRF_RD_MAX_LENGTH,
)
from .fields import VarbinaryIPField
from .querysets import IPAddressQuerySet, PrefixQuerySet, RIRQuerySet
from .validators import DNSValidator


__all__ = (
    "IPAddress",
    "Prefix",
    "RIR",
    "RouteTarget",
    "Service",
    "VLAN",
    "VLANGroup",
    "VRF",
)


logger = logging.getLogger(__name__)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "relationships",
    "webhooks",
)
class Namespace(PrimaryModel):
    """Container for unique IPAM objects."""

    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.CharField(max_length=200, blank=True)
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="namespaces",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("ipam:namespace", args=[self.pk])


def get_default_namespace():
    """Return the Global namespace for use in default value for foreign keys."""
    obj, _ = Namespace.objects.get_or_create(
        name="Global", defaults={"description": "Default Global namespace. Created by Nautobot."}
    )

    return obj.pk


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VRF(PrimaryModel):
    """
    A virtual routing and forwarding (VRF) table represents a discrete layer three forwarding domain (e.g. a routing
    table). Prefixes and IPAddresses can optionally be assigned to VRFs. (Prefixes and IPAddresses not assigned to a VRF
    are said to exist in the "global" table.)
    """

    name = models.CharField(max_length=100, db_index=True)
    rd = models.CharField(
        max_length=VRF_RD_MAX_LENGTH,
        blank=True,
        null=True,
        verbose_name="Route distinguisher",
        help_text="Unique route distinguisher (as defined in RFC 4364)",
    )
    namespace = models.ForeignKey(
        "ipam.Namespace",
        on_delete=models.PROTECT,
        related_name="vrfs",
        default=get_default_namespace,
    )
    devices = models.ManyToManyField(
        to="dcim.Device",
        related_name="vrfs",
        through="ipam.VRFDeviceAssignment",
        through_fields=("vrf", "device"),
    )
    prefixes = models.ManyToManyField(
        to="ipam.Prefix",
        related_name="vrfs",
        through="ipam.VRFPrefixAssignment",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="vrfs",
        blank=True,
        null=True,
    )
    # TODO(jathan): Nuke enforce_unique
    enforce_unique = models.BooleanField(
        default=True,
        verbose_name="Enforce unique space",
        help_text="Prevent duplicate prefixes/IP addresses within this VRF",
    )
    description = models.CharField(max_length=200, blank=True)
    import_targets = models.ManyToManyField(to="ipam.RouteTarget", related_name="importing_vrfs", blank=True)
    export_targets = models.ManyToManyField(to="ipam.RouteTarget", related_name="exporting_vrfs", blank=True)

    csv_headers = ["name", "rd", "tenant", "enforce_unique", "description"]
    clone_fields = [
        "tenant",
        "enforce_unique",
        "description",
    ]

    class Meta:
        ordering = ("namespace", "name")  # (name, rd) may be non-unique
        unique_together = [
            ["namespace", "name"],
            ["namespace", "rd"],
        ]
        verbose_name = "VRF"
        verbose_name_plural = "VRFs"

    def __str__(self):
        return self.display or super().__str__()

    def get_absolute_url(self):
        return reverse("ipam:vrf", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.rd,
            self.tenant.name if self.tenant else None,
            str(self.enforce_unique),
            self.description,
        )

    @property
    def display(self):
        if self.namespace:
            return f"{self.namespace}: ({self.name})"
        return self.name

    def add_device(self, device, rd="", name=""):
        """
        Add a `device` to this VRF, optionally overloading `rd` and `name`.

        If `rd` or `name` are not provided, the values from this VRF will be inherited.

        Args:
            device (Device): Device instance
            rd (str): (Optional) RD of the VRF when associated with this Device
            name (str): (Optional) Name of the VRF when associated with this Device

        Returns:
            VRFDeviceAssignment instance
        """
        instance = self.devices.through(vrf=self, device=device, rd=rd, name=name)
        instance.validated_save()
        return instance

    def remove_device(self, device):
        """
        Remove a `device` from this VRF.

        Args:
            device (Device): Device instance

        Returns:
            tuple (int, dict): Number of objects deleted and a dict with number of deletions.
        """
        instance = self.devices.through.objects.get(vrf=self, device=device)
        return instance.delete()

    def add_prefix(self, prefix):
        """
        Add a `prefix` to this VRF. Each object must be in the same Namespace.

        Args:
            prefix (Prefix): Prefix instance

        Returns:
            VRFPrefixAssignment instance
        """
        instance = self.prefixes.through(vrf=self, prefix=prefix)
        instance.validated_save()
        return instance

    def remove_prefix(self, prefix):
        """
        Remove a `prefix` from this VRF.

        Args:
            prefix (Prefix): Prefix instance

        Returns:
            tuple (int, dict): Number of objects deleted and a dict with number of deletions.
        """
        instance = self.prefixes.through.objects.get(vrf=self, prefix=prefix)
        return instance.delete()


class VRFDeviceAssignment(BaseModel):
    vrf = models.ForeignKey("ipam.VRF", on_delete=models.CASCADE, related_name="device_assignments")
    device = models.ForeignKey("dcim.Device", on_delete=models.CASCADE, related_name="vrf_assignments")
    rd = models.CharField(
        max_length=VRF_RD_MAX_LENGTH,
        blank=True,
        null=True,
        verbose_name="Route distinguisher",
        help_text="Unique route distinguisher (as defined in RFC 4364)",
    )
    name = models.CharField(blank=True, max_length=100)

    class Meta:
        unique_together = [
            ["vrf", "device"],
            ["device", "rd", "name"],
        ]

    def __str__(self):
        return f"{self.vrf} [{self.device}] (rd: {self.rd}, name: {self.name})"

    def clean(self):
        super().clean()

        # If RD is not set, inherit it from `vrf.rd`.
        if not self.rd:
            self.rd = self.vrf.rd

        # If name is not set, inherit it from `vrf.name`.
        if not self.name:
            self.name = self.vrf.name


class VRFPrefixAssignment(BaseModel):
    vrf = models.ForeignKey("ipam.VRF", on_delete=models.CASCADE, related_name="+")
    prefix = models.ForeignKey("ipam.Prefix", on_delete=models.CASCADE, related_name="vrf_assignments")

    class Meta:
        unique_together = ["vrf", "prefix"]

    def __str__(self):
        return f"{self.vrf}: {self.prefix}"

    def clean(self):
        super().clean()

        if self.prefix.namespace != self.vrf.namespace:
            raise ValidationError({"prefix": "Prefix must be in same namespace as VRF"})


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class RouteTarget(PrimaryModel):
    """
    A BGP extended community used to control the redistribution of routes among VRFs, as defined in RFC 4364.
    """

    name = models.CharField(
        max_length=VRF_RD_MAX_LENGTH,  # Same format options as VRF RD (RFC 4360 section 4)
        unique=True,
        help_text="Route target value (formatted in accordance with RFC 4360)",
    )
    description = models.CharField(max_length=200, blank=True)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="route_targets",
        blank=True,
        null=True,
    )

    csv_headers = ["name", "description", "tenant"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("ipam:routetarget", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.description,
            self.tenant.name if self.tenant else None,
        )


@extras_features(
    "custom_validators",
    "graphql",
)
class RIR(OrganizationalModel):
    """
    A Regional Internet Registry (RIR) is responsible for the allocation of a large portion of the global IP address
    space. This can be an organization like ARIN or RIPE, or a governing standard such as RFC 1918.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    is_private = models.BooleanField(
        default=False,
        verbose_name="Private",
        help_text="IP space managed by this RIR is considered private",
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "is_private", "description"]

    objects = BaseManager.from_queryset(RIRQuerySet)()

    class Meta:
        ordering = ["name"]
        verbose_name = "RIR"
        verbose_name_plural = "RIRs"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def get_absolute_url(self):
        return reverse("ipam:rir", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            str(self.is_private),
            self.description,
        )


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class Prefix(PrimaryModel, StatusModel, RoleModelMixin):
    """
    A Prefix represents an IPv4 or IPv6 network, including mask length.
    Prefixes can optionally be assigned to Locations and VRFs.
    A Prefix must be assigned a status and may optionally be assigned a user-defined Role.
    A Prefix can also be assigned to a VLAN where appropriate.
    Prefixes are always ordered by `namespace` and `ip_version`, then by `network` and `prefix_length`.
    """

    network = VarbinaryIPField(
        null=False,
        db_index=True,
        help_text="IPv4 or IPv6 network address",
    )
    broadcast = VarbinaryIPField(null=False, db_index=True, help_text="IPv4 or IPv6 broadcast address")
    prefix_length = models.IntegerField(null=False, db_index=True, help_text="Length of the Network prefix, in bits.")
    type = models.CharField(
        max_length=50,
        choices=choices.PrefixTypeChoices,
        default=choices.PrefixTypeChoices.TYPE_NETWORK,
    )
    parent = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        related_name="children",  # `IPAddress` to use `related_name="ip_addresses"`
        on_delete=models.PROTECT,
        help_text="The parent Prefix of this Prefix.",
    )
    # ip_version is set internally just like network, broadcast, and prefix_length.
    ip_version = models.IntegerField(
        choices=choices.IPAddressVersionChoices,
        null=True,
        editable=False,
        db_index=True,
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
    )
    namespace = models.ForeignKey(
        to="ipam.Namespace",
        on_delete=models.PROTECT,
        related_name="prefixes",
        default=get_default_namespace,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
    )
    vlan = models.ForeignKey(
        to="ipam.VLAN",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
        verbose_name="VLAN",
    )
    rir = models.ForeignKey(
        to="ipam.RIR",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
        verbose_name="RIR",
        help_text="Regional Internet Registry responsible for this prefix",
    )
    date_allocated = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date this prefix was allocated to an RIR, reserved in IPAM, etc.",
    )
    description = models.CharField(max_length=200, blank=True)

    objects = BaseManager.from_queryset(PrefixQuerySet)()

    csv_headers = [
        "prefix",
        "namespace",
        "type",
        "tenant",
        "location",
        "vlan_group",
        "vlan",
        "status",
        "role",
        "rir",
        "date_allocated",
        "description",
    ]
    clone_fields = [
        "date_allocated",
        "description",
        "location",
        "namespace",
        "rir",
        "role",
        "status",
        "tenant",
        "type",
        "vlan",
    ]
    """
    dynamic_group_filter_fields = {
        "vrf": "vrf_id",  # Duplicate filter fields that will be collapsed in 2.0
    }
    """

    class Meta:
        ordering = (
            "namespace",
            "ip_version",
            "network",
            "prefix_length",
        )
        index_together = [
            ["network", "broadcast", "prefix_length"],
            ["namespace", "network", "broadcast", "prefix_length"],
        ]
        unique_together = ["namespace", "network", "prefix_length"]
        verbose_name_plural = "prefixes"

    def validate_unique(self, exclude=None):
        if self.namespace is None:
            if Prefix.objects.filter(
                network=self.network, prefix_length=self.prefix_length, namespace__isnull=True
            ).exists():
                raise ValidationError(
                    {"__all__": "Prefix with this Namespace, Network and Prefix length already exists."}
                )
        super().validate_unique(exclude)

    def __init__(self, *args, **kwargs):
        prefix = kwargs.pop("prefix", None)
        super().__init__(*args, **kwargs)
        self._deconstruct_prefix(prefix)

    def __str__(self):
        return str(self.prefix)

    def _deconstruct_prefix(self, prefix):
        if prefix:
            if isinstance(prefix, str):
                prefix = netaddr.IPNetwork(prefix)
            # Note that our "broadcast" field is actually the last IP address in this prefix.
            # This is different from the more accurate technical meaning of a network's broadcast address in 2 cases:
            # 1. For a point-to-point prefix (IPv4 /31 or IPv6 /127), there are two addresses in the prefix,
            #    and neither one is considered a broadcast address. We store the second address as our "broadcast".
            # 2. For a host prefix (IPv6 /32 or IPv6 /128) there's only one address in the prefix.
            #    We store this address as both the network and the "broadcast".
            # This variance is intentional in both cases as we use the "broadcast" primarily for filtering and grouping
            # of addresses and prefixes, not for packet forwarding. :-)
            broadcast = prefix.broadcast if prefix.broadcast else prefix[-1]
            self.network = str(prefix.network)
            self.broadcast = str(broadcast)
            self.prefix_length = prefix.prefixlen
            self.ip_version = prefix.version

    def get_absolute_url(self):
        return reverse("ipam:prefix", args=[self.pk])

    # TODO: this function is completely unused at present - remove?
    def get_duplicates(self):
        return Prefix.objects.net_equals(self.prefix).filter(namespace=self.namespace).exclude(pk=self.pk)

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Prefixes may not associate to locations of type "{self.location.location_type}".'}
                )

    def delete(self, *args, **kwargs):
        """
        A Prefix with children will be impossible to delete and raise a `ProtectedError`.

        If a Prefix has children, this catch the error and explicitly update the
        `protected_objects` from the exception setting their parent to the old parent of this
        prefix, and then this prefix will be deleted.
        """

        try:
            return super().delete(*args, **kwargs)
        except models.ProtectedError as err:
            # This will be either IPAddress or Prefix.
            protected_model = tuple(err.protected_objects)[0]._meta.model

            # IPAddress objects must have a parent.
            if protected_model == IPAddress and self.parent is None:
                raise models.ProtectedError(
                    msg=(
                        f"Cannot delete Prefix {self} because it has child IPAddress objects that "
                        "would no longer have a parent."
                    ),
                    protected_objects=err.protected_objects,
                ) from err

            # Update protected objects to use the new parent and delete the old parent (self).
            protected_pks = (po.pk for po in err.protected_objects)
            protected_objects = protected_model.objects.filter(pk__in=protected_pks)
            protected_objects.update(parent=self.parent)
            return super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):

        if isinstance(self.prefix, netaddr.IPNetwork):

            # Clear host bits from prefix
            self.prefix = self.prefix.cidr

        # Determine if a parent exists and set it to the closest ancestor by `prefix_length`.
        supernets = self.supernets()
        if supernets:
            parent = max(supernets, key=operator.attrgetter("prefix_length"))
            self.parent = parent

        super().save(*args, **kwargs)

        # Determine the subnets and reparent them to this prefix.
        self.reparent_subnets()
        # Determine the child IPs and reparent them to this prefix.
        self.reparent_ips()

    def to_csv(self):
        return (
            self.prefix,
            self.namespace.name if self.namespace else None,
            self.get_type_display(),
            self.tenant.name if self.tenant else None,
            self.location.name if self.location else None,
            self.vlan.vlan_group.name if self.vlan and self.vlan.vlan_group else None,
            self.vlan.vid if self.vlan else None,
            self.get_status_display(),
            self.role.name if self.role else None,
            self.rir.name if self.rir else None,
            str(self.date_allocated),
            self.description,
        )

    @property
    def cidr_str(self):
        if self.network is not None and self.prefix_length is not None:
            return f"{self.network}/{self.prefix_length}"
        return None

    @property
    def prefix(self):
        if self.cidr_str:
            return netaddr.IPNetwork(self.cidr_str)
        return None

    @prefix.setter
    def prefix(self, prefix):
        self._deconstruct_prefix(prefix)

    def reparent_subnets(self):
        """
        Determine the list of child Prefixes and set the parent to self.

        This query is similiar performing update from the query returned by `subnets(direct=True)`,
        but explicitly filters for subnets of the parent of this Prefix so they can be reparented.
        """
        query = Prefix.objects.select_for_update().filter(
            ~models.Q(id=self.id),  # Don't include yourself...
            parent_id=self.parent_id,
            prefix_length__gt=self.prefix_length,
            ip_version=self.ip_version,
            network__gte=self.network,
            broadcast__lte=self.broadcast,
            namespace=self.namespace,
        )

        return query.update(parent=self)

    def reparent_ips(self):
        """Determine the list of child IPAddresses and set the parent to self."""
        query = IPAddress.objects.select_for_update().filter(
            parent_id=self.parent_id,
        )

        return query.update(parent=self)

    def supernets(self, direct=False, include_self=False, for_update=False):
        """
        Return supernets of this Prefix.

        Args:
            direct (bool): Whether to only return the direct ancestor.
            include_self (bool): Whether to include this Prefix in the list of supernets.
            for_update (bool): Lock rows until the end of any subsequent transactions.

        Returns:
            QuerySet
        """
        query = Prefix.objects.all()

        if for_update:
            query = query.select_for_update()

        if direct:
            return query.filter(id=self.parent_id)

        if not include_self:
            query = query.exclude(id=self.id)

        return query.filter(
            ip_version=self.ip_version,
            prefix_length__lte=self.prefix_length,
            network__lte=self.network,
            broadcast__gte=self.broadcast,
            namespace=self.namespace,
        )

    def subnets(self, direct=False, include_self=False, for_update=False):
        """
        Return subnets of this Prefix.

        Args:
            direct (bool): Whether to only return direct descendants.
            include_self (bool): Whether to include this Prefix in the list of subnets.
            for_update (bool): Lock rows until the end of any subsequent transactions.

        Returns:
            QuerySet
        """
        query = Prefix.objects.all()

        if for_update:
            query = query.select_for_update()

        if direct:
            return query.filter(parent_id=self.id)

        if not include_self:
            query = query.exclude(id=self.id)

        return query.filter(
            ip_version=self.ip_version,
            prefix_length__gte=self.prefix_length,
            network__gte=self.network,
            broadcast__lte=self.broadcast,
            namespace=self.namespace,
        )

    def is_child_node(self):
        """
        Returns whether I am a child node.
        """
        return self.parent is not None

    def is_leaf_node(self):
        """
        Returns whether I am leaf node (no children).
        """
        return not self.children.exists()

    def is_root_node(self):
        """
        Returns whether I am a root node (no parent).
        """
        return self.parent is None

    def ancestors(self, ascending=False, include_self=False):
        """
        Return my ancestors descending from larger to smaller prefix lengths.

        Args:
            ascending (bool): If set, reverses the return order.
            include_self (bool): Whether to include this Prefix in the list of subnets.
        """
        query = self.supernets(include_self=include_self)
        if ascending:
            query = query.reverse()
        return query

    def descendants(self, include_self=False):
        """
        Return all of my children!

        Args:
            include_self (bool): Whether to include this Prefix in the list of subnets.
        """
        return self.subnets(include_self=include_self)

    @cached_property
    def descendants_count(self):
        """Display count of descendants."""
        return self.descendants().count()

    def root(self):
        """
        Returns the root node (the parent of all of my ancestors).
        """
        return self.ancestors().first()

    def siblings(self, include_self=False):
        """
        Return my siblings. Root nodes are siblings to other root nodes.

        Args:
            include_self (bool): Whether to include this Prefix in the list of subnets.
        """
        query = Prefix.objects.filter(parent=self.parent)
        if not include_self:
            query = query.exclude(id=self.id)

        return query

    def get_child_ips(self):
        """Return all IPAddresses directly contained within this Prefix and Namespace."""
        return self.ip_addresses.all()

    def get_available_prefixes(self):
        """
        Return all available Prefixes within this prefix as an IPSet.
        """
        prefix = netaddr.IPSet(self.prefix)
        child_prefixes = netaddr.IPSet([child.prefix for child in self.descendants()])
        available_prefixes = prefix - child_prefixes

        return available_prefixes

    def get_available_ips(self):
        """
        Return all available IPs within this prefix as an IPSet.
        """
        prefix = netaddr.IPSet(self.prefix)
        child_ips = netaddr.IPSet([ip.address.ip for ip in self.get_child_ips()])
        available_ips = prefix - child_ips

        # IPv6, pool, or IPv4 /31-32 sets are fully usable
        if any(
            [
                self.ip_version == 6,
                self.type == choices.PrefixTypeChoices.TYPE_POOL,
                self.ip_version == 4 and self.prefix_length >= 31,
            ]
        ):
            return available_ips

        # Omit first and last IP address from the available set
        # For "normal" IPv4 prefixes, omit first and last addresses
        available_ips -= netaddr.IPSet(
            [
                netaddr.IPAddress(self.prefix.first),
                netaddr.IPAddress(self.prefix.last),
            ]
        )
        return available_ips

    def get_first_available_prefix(self):
        """
        Return the first available child prefix within the prefix (or None).
        """
        available_prefixes = self.get_available_prefixes()
        if not available_prefixes:
            return None
        return available_prefixes.iter_cidrs()[0]

    def get_first_available_ip(self):
        """
        Return the first available IP within the prefix (or None).
        """
        available_ips = self.get_available_ips()
        if not available_ips:
            return None
        return f"{next(available_ips.__iter__())}/{self.prefix_length}"

    def get_utilization(self):
        """Get the child prefix size and parent size.

        For Prefixes with a type of "container", get the number child prefixes. For all others, count child IP addresses.

        Returns:
            UtilizationData (namedtuple): (numerator, denominator)
        """
        if self.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            child_prefixes = netaddr.IPSet(p.prefix for p in self.descendants())
            return UtilizationData(numerator=child_prefixes.size, denominator=self.prefix.size)

        else:
            prefix_size = self.prefix.size
            if all(
                [
                    self.ip_version == 4,
                    self.prefix_length < 31,
                    self.type != choices.PrefixTypeChoices.TYPE_POOL,
                ]
            ):
                prefix_size -= 2
            child_count = prefix_size - self.get_available_ips().size
            return UtilizationData(numerator=child_count, denominator=prefix_size)


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class IPAddress(PrimaryModel, StatusModel, RoleModelMixin):
    """
    An IPAddress represents an individual IPv4 or IPv6 address and its mask. The mask length should match what is
    configured in the real world. (Typically, only loopback interfaces are configured with /32 or /128 masks.) Like
    Prefixes, IPAddresses can optionally be assigned to a VRF. An IPAddress can optionally be assigned to an Interface.
    Interfaces can have zero or more IPAddresses assigned to them.

    An IPAddress can also optionally point to a NAT inside IP, designating itself as a NAT outside IP. This is useful,
    for example, when mapping public addresses to private addresses. When an Interface has been assigned an IPAddress
    which has a NAT outside IP, that Interface's Device can use either the inside or outside IP as its primary IP.
    """

    host = VarbinaryIPField(
        null=False,
        db_index=True,
        help_text="IPv4 or IPv6 host address",
    )
    broadcast = VarbinaryIPField(null=False, db_index=True, help_text="IPv4 or IPv6 broadcast address")
    prefix_length = models.IntegerField(null=False, db_index=True, help_text="Length of the Network prefix, in bits.")
    parent = models.ForeignKey(
        "ipam.Prefix",
        blank=True,
        null=True,
        related_name="ip_addresses",  # `IPAddress` to use `related_name="ip_addresses"`
        on_delete=models.PROTECT,
        help_text="The parent Prefix of this IPAddress.",
    )
    # ip_version is set internally just like network, broadcast, and prefix_length.
    ip_version = models.IntegerField(
        choices=choices.IPAddressVersionChoices,
        null=True,
        editable=False,
        db_index=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="ip_addresses",
        blank=True,
        null=True,
    )
    nat_inside = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        related_name="nat_outside_list",
        blank=True,
        null=True,
        verbose_name="NAT (Inside)",
        help_text='The IP Addresses for which this address is the "outside" IP',
    )
    dns_name = models.CharField(
        max_length=255,
        blank=True,
        validators=[DNSValidator],
        verbose_name="DNS Name",
        help_text="Hostname or FQDN (not case-sensitive)",
        db_index=True,
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "address",
        "tenant",
        "status",
        "role",
        "is_primary",
        "dns_name",
        "description",
    ]
    clone_fields = [
        "tenant",
        "status",
        "role",
        "description",
    ]
    dynamic_group_skip_missing_fields = True  # Problematic form labels for `vminterface` and `interface`

    objects = BaseManager.from_queryset(IPAddressQuerySet)()

    class Meta:
        ordering = ("ip_version", "host", "prefix_length")  # address may be non-unique
        verbose_name = "IP address"
        verbose_name_plural = "IP addresses"
        unique_together = ["parent", "host"]

    def __init__(self, *args, **kwargs):
        address = kwargs.pop("address", None)
        namespace = kwargs.pop("namespace", None)
        # We don't want users providing their own parent since it will be derived automatically.
        parent = kwargs.pop("parent", None)
        # If namespace wasn't provided, but parent was, we'll use the parent's namespace.
        if namespace is None and parent is not None:
            namespace = parent.namespace
        self._namespace = namespace

        super().__init__(*args, **kwargs)
        self._deconstruct_address(address)

    def __str__(self):
        return str(self.address)

    def _deconstruct_address(self, address):
        if address:
            if isinstance(address, str):
                address = netaddr.IPNetwork(address)
            # Note that our "broadcast" field is actually the last IP address in this network.
            # This is different from the more accurate technical meaning of a network's broadcast address in 2 cases:
            # 1. For a point-to-point address (IPv4 /31 or IPv6 /127), there are two addresses in the network,
            #    and neither one is considered a broadcast address. We store the second address as our "broadcast".
            # 2. For a host prefix (IPv6 /32 or IPv6 /128) there's only one address in the network.
            #    We store this address as both the host and the "broadcast".
            # This variance is intentional in both cases as we use the "broadcast" primarily for filtering and grouping
            # of addresses and prefixes, not for packet forwarding. :-)
            broadcast = address.broadcast if address.broadcast else address[-1]
            self.host = str(address.ip)
            self.broadcast = str(broadcast)
            self.prefix_length = address.prefixlen
            self.ip_version = address.version

    def get_absolute_url(self):
        return reverse("ipam:ipaddress", args=[self.pk])

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def STATUS_SLAAC(cls):  # pylint: disable=no-self-argument
        """Return a cached "slaac" `Status` object for later reference."""
        cls.__status_slaac = getattr(cls, "__status_slaac", None)
        if cls.__status_slaac is None:
            try:
                cls.__status_slaac = Status.objects.get_for_model(IPAddress).get(slug="slaac")
            except Status.DoesNotExist:
                logger.error("SLAAC Status not found")
        return cls.__status_slaac

    def clean(self):
        super().clean()

        # TODO: update to work with interface M2M
        # This attribute will have been set by `IPAddressForm.clean()` to indicate that the
        # `primary_ip{version}` field on `self.assigned_object.parent` has been nullified but not yet saved.
        primary_ip_unset_by_form = getattr(self, "_primary_ip_unset_by_form", False)

        # Check for primary IP assignment that doesn't match the assigned device/VM if and only if
        # "_primary_ip_unset" has not been set by the caller.
        if self.present_in_database and not primary_ip_unset_by_form:
            device = Device.objects.filter(Q(primary_ip4=self) | Q(primary_ip6=self)).first()
            if device:
                if getattr(self.assigned_object, "device", None) != device:
                    raise ValidationError(
                        {"interface": f"IP address is primary for device {device} but not assigned to it!"}
                    )
            vm = VirtualMachine.objects.filter(Q(primary_ip4=self) | Q(primary_ip6=self)).first()
            if vm:
                if getattr(self.assigned_object, "virtual_machine", None) != vm:
                    raise ValidationError(
                        {"vminterface": f"IP address is primary for virtual machine {vm} but not assigned to it!"}
                    )

        # Validate IP status selection
        if self.status == IPAddress.STATUS_SLAAC and self.ip_version != 6:
            raise ValidationError({"status": "Only IPv6 addresses can be assigned SLAAC status"})

        # Force dns_name to lowercase
        self.dns_name = self.dns_name.lower()

    def save(self, *args, **kwargs):
        if not self.present_in_database:
            if self._namespace is None:
                raise ValidationError({"parent": "Namespace could not be determined."})
            namespace = self._namespace
        else:
            namespace = self.parent.namespace

        # Determine the closest parent automatically based on the Namespace.
        self.parent = Prefix.objects.get_closest_parent(self.host, namespace=namespace)

        super().save(*args, **kwargs)

    def to_csv(self):

        # Determine if this IP is primary for a Device
        is_primary = False
        if self.address.version == 4 and getattr(self, "primary_ip4_for", False):
            is_primary = True
        elif self.address.version == 6 and getattr(self, "primary_ip6_for", False):
            is_primary = True

        return (
            self.address,
            self.tenant.name if self.tenant else None,
            self.get_status_display(),
            self.role.name if self.role else None,
            str(is_primary),
            self.dns_name,
            self.description,
        )

    @property
    def address(self):
        if self.host is not None and self.prefix_length is not None:
            cidr = f"{self.host}/{self.prefix_length}"
            return netaddr.IPNetwork(cidr)
        return None

    @address.setter
    def address(self, address):
        self._deconstruct_address(address)

    def ancestors(self, ascending=False):
        """
        Return my ancestors descending from larger to smaller prefix lengths.

        Args:
            ascending (bool): If set, reverses the return order.
        """
        return self.parent.ancestors(include_self=True, ascending=ascending)

    @cached_property
    def ancestors_count(self):
        """Display count of ancestors."""
        return self.ancestors().count()

    def root(self):
        """
        Returns the root node (the parent of all of my ancestors).
        """
        return self.ancestors().first()

    def siblings(self, include_self=False):
        """
        Return my siblings that share the same parent Prefix.

        Args:
            include_self (bool): Whether to include this IPAddress in the list of siblings.
        """
        query = IPAddress.objects.filter(parent=self.parent)
        if not include_self:
            query = query.exclude(id=self.id)

        return query

    # 2.0 TODO: Remove exception, getter, setter below when we can safely deprecate previous properties
    class NATOutsideMultipleObjectsReturned(MultipleObjectsReturned):
        """
        An exception class is used to expose in API the object that cannot safely support the legacy getter, setter methods.
        """

        def __init__(self, obj):
            self.obj = obj

        def __str__(self):
            return f"Multiple IPAddress objects specify this object (pk: {self.obj.pk}) as nat_inside. Please refer to nat_outside_list."

    @property
    def nat_outside(self):
        if self.nat_outside_list.count() > 1:
            raise self.NATOutsideMultipleObjectsReturned(self)
        return self.nat_outside_list.first()

    @nat_outside.setter
    def nat_outside(self, value):
        if self.nat_outside_list.count() > 1:
            raise self.NATOutsideMultipleObjectsReturned(self)
        return self.nat_outside_list.set([value])

    def _set_mask_length(self, value):
        """
        Expose the IPNetwork object's prefixlen attribute on the parent model so that it can be manipulated directly,
        e.g. for bulk editing.
        """
        if self.address is not None:
            self.prefix_length = value

    mask_length = property(fset=_set_mask_length)


class IPAddressToInterface(BaseModel):
    ip_address = models.ForeignKey("ipam.IPAddress", on_delete=models.CASCADE, related_name="+")
    interface = models.ForeignKey(
        "dcim.Interface", blank=True, null=True, on_delete=models.CASCADE, related_name="ip_address_assignments"
    )
    vm_interface = models.ForeignKey(
        "virtualization.VMInterface",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="ip_address_assignments",
    )
    is_source = models.BooleanField(default=False, help_text="Is source address on interface")
    is_destination = models.BooleanField(default=False, help_text="Is destination address on interface")
    is_default = models.BooleanField(default=False, help_text="Is default address on interface")
    is_preferred = models.BooleanField(default=False, help_text="Is preferred address on interface")
    is_primary = models.BooleanField(default=False, help_text="Is primary address on interface")
    is_secondary = models.BooleanField(default=False, help_text="Is secondary address on interface")
    is_standby = models.BooleanField(default=False, help_text="Is standby address on interface")

    def validate_unique(self, exclude=None):
        """
        Check uniqueness on combination of `ip_address`, `interface` and `vm_interface` fields
        and raise ValidationError if check failed.
        """
        if IPAddressToInterface.objects.filter(
            ip_address=self.ip_address,
            interface=self.interface,
            vm_interface=self.vm_interface,
        ).exists():
            raise ValidationError(
                "IPAddressToInterface with this ip_address, interface and vm_interface already exists."
            )

    def clean(self):
        super().clean()

        if self.interface is not None and self.vm_interface is not None:
            raise ValidationError(
                {"interface": "Cannot use a single instance to associate to both an Interface and a VMInterface."}
            )

        if self.interface is None and self.vm_interface is None:
            raise ValidationError({"interface": "Must associate to either an Interface or a VMInterface."})

    def __str__(self):
        if self.interface:
            return f"{self.ip_address!s} {self.interface.device.name} {self.interface.name}"
        else:
            return f"{self.ip_address!s} {self.vm_interface.virtual_machine.name} {self.vm_interface.name}"


@extras_features(
    "custom_validators",
    "graphql",
    "locations",
)
class VLANGroup(OrganizationalModel):
    """
    A VLAN group is an arbitrary collection of VLANs within which VLAN IDs and names must be unique.
    """

    name = models.CharField(max_length=100, db_index=True)
    # 2.0 TODO: Remove unique=None to make slug globally unique. This would be a breaking change.
    slug = AutoSlugField(populate_from="name", unique=None, db_index=True)
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="vlan_groups",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "location", "description"]

    class Meta:
        ordering = (
            "location",
            "name",
        )  # (location, name) may be non-unique
        unique_together = [
            # 2.0 TODO: since location is nullable, and NULL != NULL, this means that we can have multiple non-Location VLANGroups
            # with the same name. This should probably be fixed with a custom validate_unique() function!
            ["location", "name"],
            # 2.0 TODO: Remove unique_together to make slug globally unique. This would be a breaking change.
            ["location", "slug"],
        ]
        verbose_name = "VLAN group"
        verbose_name_plural = "VLAN groups"

    natural_key_field_names = ["name", "location"]  # location needs to be last since it's a variadic natural key

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'VLAN groups may not associate to locations of type "{self.location.location_type}".'}
                )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("ipam:vlangroup", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.location.name if self.location else None,
            self.description,
        )

    def get_next_available_vid(self):
        """
        Return the first available VLAN ID (1-4094) in the group.
        """
        vlan_ids = VLAN.objects.filter(vlan_group=self).values_list("vid", flat=True)
        for i in range(1, 4095):
            if i not in vlan_ids:
                return i
        return None


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class VLAN(PrimaryModel, StatusModel, RoleModelMixin):
    """
    A VLAN is a distinct layer two forwarding domain identified by a 12-bit integer (1-4094).
    Each VLAN must be assigned to a Location, however VLAN IDs need not be unique within a Location.
    A VLAN may optionally be assigned to a VLANGroup, within which all VLAN IDs and names but be unique.

    Like Prefixes, each VLAN is assigned an operational status and optionally a user-defined Role. A VLAN can have zero
    or more Prefixes assigned to it.
    """

    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="vlans",
        blank=True,
        null=True,
    )
    vlan_group = models.ForeignKey(
        to="ipam.VLANGroup",
        on_delete=models.PROTECT,
        related_name="vlans",
        blank=True,
        null=True,
    )
    vid = models.PositiveSmallIntegerField(
        verbose_name="ID", validators=[MinValueValidator(1), MaxValueValidator(4094)]
    )
    name = models.CharField(max_length=255, db_index=True)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="vlans",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "location",
        "vlan_group",
        "vid",
        "name",
        "tenant",
        "status",
        "role",
        "description",
    ]
    clone_fields = [
        "location",
        "vlan_group",
        "tenant",
        "status",
        "role",
        "description",
    ]

    class Meta:
        ordering = (
            "location",
            "vlan_group",
            "vid",
        )  # (location, group, vid) may be non-unique
        unique_together = [
            # 2.0 TODO: since group is nullable and NULL != NULL, we can have multiple non-group VLANs with
            # the same vid and name. We should probably fix this with a custom validate_unique() function.
            ["vlan_group", "vid"],
            ["vlan_group", "name"],
        ]
        verbose_name = "VLAN"
        verbose_name_plural = "VLANs"

    def __str__(self):
        return self.display or super().__str__()

    def get_absolute_url(self):
        return reverse("ipam:vlan", args=[self.pk])

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'VLANs may not associate to locations of type "{self.location.location_type}".'}
                )

        # Validate VLAN group
        if (
            self.vlan_group is not None
            and self.location is not None
            and self.vlan_group.location is not None
            and self.vlan_group.location not in self.location.ancestors(include_self=True)
        ):
            raise ValidationError(
                {
                    "vlan_group": f'The assigned group belongs to a location that does not include location "{self.location}".'
                }
            )

    def to_csv(self):
        return (
            self.location.name if self.location else None,
            self.vlan_group.name if self.vlan_group else None,
            self.vid,
            self.name,
            self.tenant.name if self.tenant else None,
            self.get_status_display(),
            self.role.name if self.role else None,
            self.description,
        )

    @property
    def display(self):
        return f"{self.name} ({self.vid})"

    def get_interfaces(self):
        # Return all device interfaces assigned to this VLAN
        return Interface.objects.filter(Q(untagged_vlan_id=self.pk) | Q(tagged_vlans=self.pk)).distinct()

    def get_vminterfaces(self):
        # Return all VM interfaces assigned to this VLAN
        return VMInterface.objects.filter(Q(untagged_vlan_id=self.pk) | Q(tagged_vlans=self.pk)).distinct()


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class Service(PrimaryModel):
    """
    A Service represents a layer-four service (e.g. HTTP or SSH) running on a Device or VirtualMachine. A Service may
    optionally be tied to one or more specific IPAddresses belonging to its parent.
    """

    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="device",
        null=True,
        blank=True,
    )
    virtual_machine = models.ForeignKey(
        to="virtualization.VirtualMachine",
        on_delete=models.CASCADE,
        related_name="services",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100, db_index=True)
    protocol = models.CharField(max_length=50, choices=choices.ServiceProtocolChoices)
    ports = JSONArrayField(
        base_field=models.PositiveIntegerField(
            validators=[
                MinValueValidator(SERVICE_PORT_MIN),
                MaxValueValidator(SERVICE_PORT_MAX),
            ]
        ),
        verbose_name="Port numbers",
    )
    ip_addresses = models.ManyToManyField(
        to="ipam.IPAddress",
        related_name="services",
        blank=True,
        verbose_name="IP addresses",
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "device",
        "virtual_machine",
        "name",
        "protocol",
        "ports",
        "description",
    ]

    class Meta:
        ordering = (
            "protocol",
            "ports",
        )  # (protocol, port) may be non-unique

    def __str__(self):
        return f"{self.name} ({self.get_protocol_display()}/{self.port_list})"

    def get_absolute_url(self):
        return reverse("ipam:service", args=[self.pk])

    @property
    def parent(self):
        return self.device or self.virtual_machine

    def clean(self):
        super().clean()

        # A Service must belong to a Device *or* to a VirtualMachine
        if self.device and self.virtual_machine:
            raise ValidationError("A service cannot be associated with both a device and a virtual machine.")
        if not self.device and not self.virtual_machine:
            raise ValidationError("A service must be associated with either a device or a virtual machine.")

    def to_csv(self):
        return (
            self.device.name if self.device else None,
            self.virtual_machine.name if self.virtual_machine else None,
            self.name,
            self.get_protocol_display(),
            self.ports,
            self.description,
        )

    @property
    def port_list(self):
        return array_to_string(self.ports)
