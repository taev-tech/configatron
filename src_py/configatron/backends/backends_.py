from collections.abc import Collection
from collections.abc import Mapping
from typing import ClassVar
from typing import Protocol


class _ConfigBackendBase(Protocol):

    allow_secret: ClassVar[bool]
    allow_unsecured: ClassVar[bool]
    name: str

    def __init__(self, *, name: str): ...


class SyncConfigBackend(_ConfigBackendBase, Protocol):

    def load_sync(
            self,
            keyspace: Mapping[str, Collection[str]]
            ) -> Mapping[str, Collection[str]]:
        """Loads ^^at least^^ the values requested in the keyspace.
        May return more values if desired; as long as they are valid
        for this particular backend, and known values for configs, these
        extra values will also be refreshed. This can be useful if the
        backend stores multiple configuration keys under a single
        storage entry.

        Note that both the passed ``keyspace`` and the return value
        are structured as a ``{namespace: [key1, key2]}`` mapping.
        """
        ...


class AyncConfigBackend(_ConfigBackendBase, Protocol):

    async def load_async(
            self,
            keyspace: Mapping[str, Collection[str]]
            ) -> Mapping[str, Collection[str]]:
        """Loads ^^at least^^ the values requested in the keyspace.
        May return more values if desired; as long as they are valid
        for this particular backend, and known values for configs, these
        extra values will also be refreshed. This can be useful if the
        backend stores multiple configuration keys under a single
        storage entry.

        Note that both the passed ``keyspace`` and the return value
        are structured as a ``{namespace: [key1, key2]}`` mapping.
        """
        ...
