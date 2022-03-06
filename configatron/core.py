'''Contains the core API for configatron. These are all imported into
__init__ and included in the toplevel package __all__.
'''
import dataclasses
import enum
import functools
from typing import (
    Any,
    Optional)

from configatron._runtime_state import (
    get_loaded_config,
    RawLookupKey)
from configatron.exceptions import (
    ConfigatronInternalError)


# Used as a sentinel when the value doesn't appear in the config
_MISSING = object()


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

        value_proxy = _LoadedConfigatronValueProxy(
            backend=None, namespace=namespace, metadata=metadata)
        # Update the class -- NOT the instance -- with a non-data descriptor
        # for the value. This should preserve instance value lookup, so only
        # on the class itself will we be trying to access the values. Note that
        # dataclasses do **not** add the fields to the class, so there's no
        # conflict here.
        setattr(cls, field.name, value_proxy)

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


secret = functools.partial(
    _collect_medatada_into_field, _configatron_mode=_ConfigatronMode.SECRET)
unsecured = functools.partial(
    _collect_medatada_into_field, _configatron_mode=_ConfigatronMode.UNSECURED)


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


class _LoadedConfigatronValueProxy:

    def __init__(self, backend, namespace, metadata):
        self._backend = backend
        self._namespace = namespace
        self._metadata = metadata
        self._field_name = None

    def __set_name__(self, owner, name):
        self._field_name = name

    def __get__(self, obj, objtype=None):
        if obj is not None:
            raise ConfigatronInternalError(
                'Somehow you managed to directly access the configatron ' +
                'value proxy? Please report to configatron maintainers!')

        loaded_config = get_loaded_config()

        primary_key = RawLookupKey(
            backend=self._backend,
            namespace=self._namespace,
            name=self._metadata.primary_name)
        secondary_key = RawLookupKey(
            backend=self._backend,
            namespace=self._namespace,
            name=self._metadata.secondary_name)

        loaded_value = loaded_config.get(primary_key, _MISSING)
        if loaded_value is _MISSING:
            loaded_value = loaded_config.get(secondary_key, _MISSING)
        if loaded_value is _MISSING:
            raise ConfigatronInternalError(
                'Configatron allowed you to load an incomplete config!')

        return loaded_value
