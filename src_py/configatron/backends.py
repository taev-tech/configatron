from __future__ import annotations

import itertools
from collections.abc import Mapping
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import Protocol

from configatron.types import CfgFieldDesc
from configatron.types import CfgSource


@dataclass(slots=True, frozen=True)
class KeyspaceSummary:
    """Used during loading to describe both the entire keyspace, and the
    specific requested fields.
    """
    by_namespace: Mapping[str | None, Sequence[tuple[CfgFieldDesc, CfgSource]]]

    @property
    def flattened(self) -> Sequence[tuple[CfgFieldDesc, CfgSource]]:
        return tuple(itertools.chain.from_iterable(self.by_namespace.values()))


class CfgBackend(Protocol):
    ALLOW_SECRET: ClassVar[bool]
    ALLOW_PLAINTEXT: ClassVar[bool]

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
        ...

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
        ...
