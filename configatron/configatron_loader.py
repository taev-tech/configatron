import collections
import dataclasses
from contextlib import contextmanager

from configatron._runtime_state import _LOADED_CONFIG
from configatron.configatron_ import ensure_sufficient_keyspace
from configatron.configatron_ import get_complete_keyspace


@dataclasses.dataclass
class _ConfigState:
    fully_loaded: bool
    lookup: dict


class ConfigatronLoader:

    def __init__(self, backends):
        self.backends = backends

    @contextmanager
    def load(self):
        keyspace = get_complete_keyspace()
        backends = iter(self.backends)
        first_backend = next(backends)
        # We do this incrementally so that each config has access to the
        # results of the previous configs
        lookup = collections.ChainMap(first_backend.load(keyspace=keyspace))
        state = _ConfigState(fully_loaded=False, lookup=lookup)
        token = _LOADED_CONFIG.set(state)
        try:
            for remaining_backend in backends:
                lookup.maps.append(remaining_backend.load(keyspace=keyspace))

            ensure_sufficient_keyspace(lookup)

            yield self
        finally:
            _LOADED_CONFIG.reset(token)
