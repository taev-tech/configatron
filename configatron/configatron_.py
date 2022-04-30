'''Contains the core API for configatron. These are all imported into
__init__ and included in the toplevel package __all__.
'''
import dataclasses
import enum
import functools
from typing import Any
from typing import Optional
from collections.abc import Iterable

import configatron._runtime_state as runtime_state
from configatron._runtime_state import get_loaded_config
from configatron._runtime_state import RawLookupKey
from configatron.exceptions import ConfigatronInternalError
from configatron.exceptions import ConfigKeyNotFound
from configatron.exceptions import InvalidConfigatronDefinition


_DATACLASS_METADATA_KEY = 'configatron'
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
    if namespace in runtime_state.ALL_CONFIGATRONS:
        raise InvalidConfigatronDefinition(
            'Cannot duplicate config namespaces!')

    configatron = dataclasses.dataclass(frozen=True, eq=False)(cls)
    # Dynamic configs can be mutated, so make sure we're not hashable
    configatron.__hash__ = None

    flattened_config_keys = set()
    for field in dataclasses.fields(configatron):
        metadata = field.metadata.get(_DATACLASS_METADATA_KEY)
        if metadata is None:
            raise InvalidConfigatronDefinition(
                'All config fields must be a configatron field!')

        if metadata.config_key is None:
            metadata.config_key = field.name

        if any(key in flattened_config_keys for key in metadata.config_keys()):
            raise InvalidConfigatronDefinition(
                'Cannot have duplicate config keys within the same namespace!')
        flattened_config_keys.update(metadata.config_keys())

        value_proxy = _LoadedConfigatronValueProxy(
            namespace=namespace, metadata=metadata)
        # Update the class -- NOT the instance -- with a non-data descriptor
        # for the value. This should preserve instance value lookup, so only
        # on the class itself will we be trying to access the values. Note that
        # dataclasses do **not** add the fields to the class, so there's no
        # conflict here.
        setattr(cls, field.name, value_proxy)

    configatron.__configatron_namespace__ = namespace
    runtime_state.ALL_CONFIGATRONS[namespace] = configatron

    return configatron


def get_keyspace(backend):
    """Returns all possible keys, including secondaries. NOTE: this
    must be run AFTER importing all defined configatron classes!
    """
    return tuple(_get_keyspace(backend))


def _get_keyspace(backend):
    """Inner iterator. Used by the above to construct a tuple."""
    for namespace, configatron in runtime_state.ALL_CONFIGATRONS.items():
        for config_field in dataclasses.fields(configatron):
            metadata = config_field.metadata[_DATACLASS_METADATA_KEY]
            if metadata.supported_by_backend(backend):
                for name in metadata.config_keys():
                    yield RawLookupKey(namespace=namespace, name=name)


def ensure_complete_config(lookup):
    """Checks to make sure that the lookup has values for all config
    keys. For primary/secondary, only requires a single of the pair.
    Raises if keys are missing.
    """
    missing_fields = []
    for namespace, configatron in runtime_state.ALL_CONFIGATRONS.items():
        for config_field in dataclasses.fields(configatron):
            metadata = config_field.metadata[_DATACLASS_METADATA_KEY]
            if not any(
                    RawLookupKey(namespace=namespace, name=name) in lookup
                    for name in metadata.config_keys()):
                missing_fields.append(metadata)

    if missing_fields:
        raise ConfigKeyNotFound(missing_fields)

    return True


class _ConfigatronMode(enum.Enum):
    UNSECURED = enum.auto()
    SECRET = enum.auto()


def _collect_medatada_into_field(
        *, _configatron_mode, default=dataclasses.MISSING,
        default_factory=dataclasses.MISSING, dynamic=False,
        config_key=None, alt_config_keys=None, backend_kwargs=None):
    '''Collect all of the Configatron-relevant metadata and package it
    into a single object, returning a dataclass field with the metadata
    stored there as, well, metadata.
    '''
    metadata = _ConfigatronMetadata(
        configatron_mode=_configatron_mode,
        dynamic=dynamic,
        config_key=config_key,
        alt_config_keys=alt_config_keys,
        backend_kwargs=backend_kwargs)

    return dataclasses.field(
        default=default,
        default_factory=default_factory,
        metadata={_DATACLASS_METADATA_KEY: metadata})


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
    config_key: Optional[str] = None
    alt_config_keys: Optional[Iterable[str]] = None

    backend_kwargs: Optional[dict[str, Any]] = dataclasses.field(
        default_factory=dict)

    def __post_init__(self):
        if self.dynamic:
            raise NotImplementedError()

    def config_keys(self):
        """Yields first the primary key, then any alternate key(s)
        (but only if they exist), in order.
        """
        yield self.config_key
        if self.alt_config_keys is not None:
            yield from self.alt_config_keys

    def supported_by_backend(self, backend):
        return (
            (self.configatron_mode is _ConfigatronMode.UNSECURED
                and backend.allow_unsecured)
            or (self.configatron_mode is _ConfigatronMode.SECRET
                and backend.allow_secret)
        )


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

        loaded_value = _MISSING
        for key_name in self._metadata.config_keys():
            lookup_key = RawLookupKey(namespace=self._namespace, name=key_name)
            loaded_value = loaded_config.get(lookup_key, _MISSING)

            if loaded_value is not _MISSING:
                break

        if loaded_value is _MISSING:
            raise ConfigatronInternalError(
                'Configatron allowed you to load an incomplete config!')

        return loaded_value
