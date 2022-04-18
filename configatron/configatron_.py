'''Contains the core API for configatron. These are all imported into
__init__ and included in the toplevel package __all__.
'''
import dataclasses
import enum
import functools
from typing import (
    Any,
    Optional)

from configatron._runtime_state import get_loaded_config
from configatron._runtime_state import RawLookupKey
from configatron.exceptions import ConfigatronInternalError
from configatron.exceptions import ConfigKeyNotFound
from configatron.exceptions import InvalidConfigatronDefinition


# Used as a sentinel when the value doesn't appear in the config
_MISSING = object()
_ALL_CONFIGATRONS = {}


def configatron(*, namespace):
    def decorator_closure(cls):
        return _make_configatron(cls, namespace)

    return decorator_closure


@dataclasses.dataclass(frozen=True)
class _DualNameKey:
    primary_name: str
    secondary_name: Optional[str] = None

    def __iter__(self):
        yield self.primary_name
        if self.secondary_name is not None:
            yield self.secondary_name


def _make_configatron(cls, namespace):
    """This is responsible for the actual logic of assembling a
    configatron class, separated out from the decorator for ease of
    testing.
    """
    if namespace in _ALL_CONFIGATRONS:
        raise InvalidConfigatronDefinition(
            'Cannot duplicate config namespaces!')

    configatron = dataclasses.dataclass(frozen=True, eq=False)(cls)
    # Dynamic configs can be mutated, so make sure we're not hashable
    configatron.__hash__ = None

    keyspace = []
    for field in dataclasses.fields(configatron):
        metadata = field.metadata.get('configatron')
        if metadata is None:
            raise InvalidConfigatronDefinition(
                'All config fields must be a configatron field!')

        if metadata.primary_name is None:
            metadata.primary_name = field.name

        value_proxy = _LoadedConfigatronValueProxy(
            namespace=namespace, metadata=metadata)
        # Update the class -- NOT the instance -- with a non-data descriptor
        # for the value. This should preserve instance value lookup, so only
        # on the class itself will we be trying to access the values. Note that
        # dataclasses do **not** add the fields to the class, so there's no
        # conflict here.
        setattr(cls, field.name, value_proxy)

        key = _DualNameKey(metadata.primary_name, metadata.secondary_name)
        keyspace.append(key)

    configatron.__configatron_namespace__ = namespace
    configatron.__configatron_keyspace__ = tuple(keyspace)
    _ALL_CONFIGATRONS[namespace] = configatron

    return configatron


def get_complete_keyspace():
    """Returns all possible keys, including secondaries. NOTE: this
    must be run AFTER importing all defined configatron classes!
    """
    return tuple(_get_complete_keyspace())


def _get_complete_keyspace():
    """Inner iterator. Used by the above to construct a tuple."""
    for namespace, configatron in _ALL_CONFIGATRONS.items():
        keyspace_for_config = configatron.__configatron_keyspace__
        for dual_name_key in keyspace_for_config:
            for name in dual_name_key:
                yield RawLookupKey(namespace=namespace, name=name)


def ensure_sufficient_keyspace(lookup):
    """Checks to make sure that the lookup has values for all config
    keys. For primary/secondary, only requires a single of the pair.
    Raises if keys are missing.
    """
    missing_keys = set()
    for namespace, configatron in _ALL_CONFIGATRONS.items():
        keyspace_for_config = configatron.__configatron_keyspace__
        for dual_name_key in keyspace_for_config:
            if not any(name in lookup for name in dual_name_key):
                missing_keys.add(dual_name_key)

    if missing_keys:
        raise ConfigKeyNotFound(missing_keys)

    return True


class _ConfigatronMode(enum.Enum):
    UNSECURED = enum.auto()
    SECRET = enum.auto()


def _collect_medatada_into_field(
        *, _configatron_mode, default=dataclasses.MISSING,
        default_factory=dataclasses.MISSING, dynamic=False,
        primary_name=None, secondary_name=None, backend_kwargs=None):
    '''Collect all of the Configatron-relevant metadata and package it
    into a single object, returning a dataclass field with the metadata
    stored there as, well, metadata.
    '''
    metadata = _ConfigatronMetadata(
        configatron_mode=_configatron_mode,
        dynamic=dynamic,
        primary_name=primary_name,
        secondary_name=secondary_name,
        backend_kwargs=backend_kwargs)

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
    backend_kwargs: Optional[dict[str, Any]] = dataclasses.field(
        default_factory=dict)

    def __post_init__(self):
        if self.dynamic:
            raise NotImplementedError()


class _LoadedConfigatronValueProxy:

    def __init__(self, namespace, metadata):
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
            namespace=self._namespace,
            name=self._metadata.primary_name)
        secondary_key = RawLookupKey(
            namespace=self._namespace,
            name=self._metadata.secondary_name)

        loaded_value = loaded_config.get(primary_key, _MISSING)
        if loaded_value is _MISSING:
            loaded_value = loaded_config.get(secondary_key, _MISSING)
        if loaded_value is _MISSING:
            raise ConfigatronInternalError(
                'Configatron allowed you to load an incomplete config!')

        return loaded_value
