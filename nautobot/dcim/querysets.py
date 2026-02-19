from nautobot.core.models.querysets import ClusterToClustersQuerySetMixin, RestrictedQuerySet
from nautobot.extras.querysets import ConfigContextModelQuerySet


class DeviceQuerySet(ClusterToClustersQuerySetMixin, ConfigContextModelQuerySet):
    pass


class ModuleQuerySet(RestrictedQuerySet):
    """QuerySet for Module that translates component reverse-relation lookups.

    Since the `module` FK moved from each component's table to the CableTermination
    base table, Django's ORM no longer auto-creates per-component reverse managers
    on Module (e.g. `interfaces`, `console_ports`).  Instead, all components are
    reachable via the single `cable_terminations` reverse relation and then an MTI
    downcast.

    This queryset intercepts filter/exclude kwargs and rewrites the old shorthand
    paths so that existing code like ``Module.objects.filter(interfaces__name=...)``
    keeps working.
    """

    # Maps old reverse-manager name → ORM path through cable_terminations + MTI downcast
    _COMPONENT_LOOKUP_MAP = {
        "interfaces": "cable_terminations__interface",
        "console_ports": "cable_terminations__consoleport",
        "console_server_ports": "cable_terminations__consoleserverport",
        "power_ports": "cable_terminations__powerport",
        "power_outlets": "cable_terminations__poweroutlet",
        "front_ports": "cable_terminations__frontport",
        "rear_ports": "cable_terminations__rearport",
        "power_feeds": "cable_terminations__powerfeed",
    }

    @classmethod
    def _translate_kwargs(cls, kwargs):
        translated = {}
        for key, value in kwargs.items():
            new_key = key
            for old_prefix, new_prefix in cls._COMPONENT_LOOKUP_MAP.items():
                if key == old_prefix or key.startswith(old_prefix + "__"):
                    new_key = new_prefix + key[len(old_prefix):]
                    break
            translated[new_key] = value
        return translated

    def filter(self, *args, **kwargs):
        return super().filter(*args, **self._translate_kwargs(kwargs))

    def exclude(self, *args, **kwargs):
        return super().exclude(*args, **self._translate_kwargs(kwargs))
