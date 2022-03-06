import dataclasses
from contextvars import ContextVar
from typing import Any

from configatron.exceptions import ConfigNotLoaded


_LOADED_CONFIG: ContextVar[dict] = ContextVar('_LOADED_CONFIG', default=None)


def get_loaded_config():
    loaded_config = _LOADED_CONFIG.get()
    if loaded_config is None:
        raise ConfigNotLoaded(
            'Attempt to access config value before config was loaded!')
    else:
        return loaded_config


@dataclasses.dataclass(frozen=True)
class RawLookupKey:
    """Use this class to perform key lookups against a raw config."""
    backend: Any
    namespace: str
    name: str
