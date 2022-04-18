from collections.abc import Iterable
from typing import Protocol
from typing import runtime_checkable

from configatron._runtime_state import RawLookupKey


@runtime_checkable
class ConfigatronBackend(Protocol):

    allow_secret: bool
    allow_unsecured: bool

    def load(self, keyspace: Iterable[RawLookupKey]):
        """Receives a list of all possible values. Load all of the
        values available on the backend. Return a dict-like lookup that
        converts from RawLookupKeys to raw config values.

        The loaded values should be strict, ie, additional values should
        not be included. If you include additional values, you may break
        some protections (for example, you may accidentally allow a
        secret to be stored on a backend that only supports unsecured
        config values).
        """
        ...
