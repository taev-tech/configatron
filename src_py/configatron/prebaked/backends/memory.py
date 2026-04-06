from __future__ import annotations

import typing
from dataclasses import dataclass
from dataclasses import field
from typing import Any
from typing import Self

from configatron.backends import CfgBackend
from configatron.backends import KeyspaceSummary
from configatron.types import CfgFieldDesc

try:
    import anyio
except ImportError:
    if typing.TYPE_CHECKING:
        import anyio


@dataclass(slots=True, frozen=True)
class MemoryBackendKey:
    namespace: str | None
    fieldname: str
    primary_lookup_key: str

    @classmethod
    def map_keyspace_summary(
            cls,
            keyspace: KeyspaceSummary
            ) -> dict[Self, CfgFieldDesc]:
        return {
            cls(
                field_tuple[0].namespace,
                field_tuple[0].name,
                field_tuple[1].lookup_keys[0]
            ):
                field_tuple[0]
            for field_tuple in keyspace.flattened}


@dataclass(slots=True)
class MemoryBackend(CfgBackend):
    """In-memory backends are intended for use in testing, though they
    might also be useful in some other situations.
    """
    ALLOW_SECRET = True
    ALLOW_PLAINTEXT = True

    values: dict[MemoryBackendKey, Any] = field(default_factory=dict)

    def load_sync(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        """Loads values from a config backend.

        This is passed both a request, and the full keyspace. The full
        keyspace is the complete set of all values that the config
        manager knows about. The request is the current set of fields
        that need to be loaded (possibly after applying some
        backend-specific filtering).

        Backends must return all of the values they have available for
        the passed request. They may also (optionally) include addition
        values outside the request, but included in the full keyspace;
        this can be useful if the particular backend responds with extra
        keys and you don't want to waste the lookup.
        """
        mapped_keys = MemoryBackendKey.map_keyspace_summary(full_keyspace)
        return {
            mapped_keys[key]: value
            for key, value in self.values.items()
            if key in mapped_keys}

    async def load_async(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        """Loads values from a config backend.

        This is passed both a request, and the full keyspace. The full
        keyspace is the complete set of all values that the config
        manager knows about. The request is the current set of fields
        that need to be loaded (possibly after applying some
        backend-specific filtering).

        Backends must return all of the values they have available for
        the passed request. They may also (optionally) include addition
        values outside the request, but included in the full keyspace;
        this can be useful if the particular backend responds with extra
        keys and you don't want to waste the lookup.
        """
        await anyio.sleep(0)
        mapped_keys = MemoryBackendKey.map_keyspace_summary(full_keyspace)
        return {
            mapped_keys[key]: value
            for key, value in self.values.items()
            if key in mapped_keys}
