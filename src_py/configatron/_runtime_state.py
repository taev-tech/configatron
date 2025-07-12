import dataclasses
from contextvars import ContextVar

from configatron.exceptions import ConfigNotLoaded

_LOADED_CONFIG: ContextVar[dict] = ContextVar('_LOADED_CONFIG', default=None)
ALL_CONFIGATRONS = {}


def get_loaded_config(namepsace, *, allow_partial=False):
    """Return the loaded config for the namespace. Raise ConfigNotLoaded
    if no config has been loaded, and UnknownNamespace if we don't have
    a config defined for that namespace.
    """
    loaded_config = _LOADED_CONFIG.get()
    if loaded_config is None:
        raise ConfigNotLoaded(
            'Attempt to access config value before config was loaded!')

    elif not loaded_config.fully_loaded and not allow_partial:
        raise ConfigNotLoaded(
            'Attempt to access partially-loaded config value without ' +
            'allow_partial!')

    else:
        return loaded_config.lookup


@dataclasses.dataclass(frozen=True)
class RawLookupKey:
    """Use this class to perform key lookups against a raw config."""
    namespace: str
    name: str
