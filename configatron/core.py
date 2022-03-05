'''Contains the core API for configatron. These are all imported into
__init__ and included in the toplevel package __all__.
'''
import dataclasses
import functools
from typing import (
    Annotated,
    Any,
    Optional)


def _collect_medatada(
        typ=None, /, _metadata_collector_class, dynamic=False,
        backend_alias=None, backend_args=None):
    collected_metadata = _metadata_collector_class(
        dynamic=dynamic,
        backend_alias=backend_alias,
        backend_args=backend_args)

    if typ is None:
        return collected_metadata

    else:
        return Annotated[typ, collected_metadata]


@dataclasses.dataclass
class _ConfigMetadataCollector:
    dynamic: bool
    backend_alias: Optional[str]
    backend_args: dict[str, Any]


class ConfigFieldSecret(_ConfigMetadataCollector):
    pass


class ConfigFieldUnsecured(_ConfigMetadataCollector):
    pass


secret = functools.partial(
    _collect_metadata, _metadata_collector_class=ConfigFieldSecret)
unsecured = functools.partial(
    _collect_metadata, _metadata_collector_class=ConfigFieldUnsecured)
