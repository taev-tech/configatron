'''Contains the core API for configatron. These are all imported into
__init__ and included in the toplevel package __all__.
'''
import dataclasses
import enum
import functools
from typing import (
    Any,
    Optional)


def configatron(*, namespace):
    def decorator_closure(cls):
        return _make_configatron(cls, namespace)

    return decorator_closure


def _make_configatron(cls, namespace):
    """This is responsible for the actual logic of assembling a
    configatron class, separated out from the decorator for ease of
    testing.
    """
    configatron = dataclasses.dataclass(frozen=True, eq=False)(cls)
    # Dynamic configs can be mutated, so make sure we're not hashable
    configatron.__hash__ = None

    for field in dataclasses.fields(configatron):
        metadata = field.metadata.get('configatron')
        if metadata is None:
            raise TypeError('All config fields must be a configatron field!')

        if metadata.primary_name is None:
            metadata.primary_name = field.name

    configatron.__configatron_namespace__ = namespace

    return configatron


class _ConfigatronMode(enum.Enum):
    UNSECURED = enum.auto()
    SECRET = enum.auto()


def _collect_medatada_into_field(
        *, _configatron_mode, default=dataclasses.MISSING,
        default_factory=dataclasses.MISSING, dynamic=False,
        primary_name=None, secondary_name=None, backend_args=None):
    '''Collect all of the Configatron-relevant metadata and package it
    into a single object, returning a dataclass field with the metadata
    stored there as, well, metadata.
    '''
    metadata = _ConfigatronMetadata(
        configatron_mode=_configatron_mode,
        dynamic=dynamic,
        primary_name=primary_name,
        secondary_name=secondary_name,
        backend_args=backend_args)

    return dataclasses.field(
        default=default,
        default_factory=default_factory,
        metadata={'configatron': metadata})


@dataclasses.dataclass
class _ConfigatronMetadata:
    configatron_mode: _ConfigatronMode
    dynamic: bool
    # Note: if this is None, we will infer it based on the field name during
    # creation
    primary_name: Optional[str] = None
    secondary_name: Optional[str] = None
    backend_args: Optional[dict[str, Any]] = dataclasses.field(
        default_factory=dict)

    def __post_init__(self):
        if self.dynamic:
            raise NotImplementedError()


secret = functools.partial(
    _collect_medatada_into_field, _configatron_mode=_ConfigatronMode.SECRET)
unsecured = functools.partial(
    _collect_medatada_into_field, _configatron_mode=_ConfigatronMode.UNSECURED)
