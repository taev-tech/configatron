from __future__ import annotations

import json
import typing
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from configatron.backends import CfgBackend
from configatron.backends import KeyspaceSummary
from configatron.types import CfgFieldDesc

try:
    import anyio
except ImportError:
    if typing.TYPE_CHECKING:
        import anyio


@dataclass(slots=True)
class JsonFileBackend(CfgBackend):
    """A config backend that uses a json file for storing config values.
    Supports plaintext (ie non-secret) configs only.

    This will always check the first (and only the first) lookup key in
    the config sources.

    Namespaces are interpreted as the names of keys in the toplevel
    toml dictionary. So for example, ``None -> foo, my_namespace -> bar``
    would expect a toml document formatted like this:

    > Example toml document
    __embed__: 'markup/toml'
        # Implicit namespace=None
        foo = "oof"

        [my_namespace]
        bar = "rab"
    """
    ALLOW_SECRET = False
    ALLOW_PLAINTEXT = True

    file_path: str | Path

    def load_sync(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        if isinstance(self.file_path, str):
            file_path = Path(self.file_path)
        else:
            file_path = self.file_path

        json_text = file_path.read_text('utf-8')
        return self._load(json_text, request, full_keyspace)

    async def load_async(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        file_path = anyio.Path(self.file_path)
        json_text = await file_path.read_text('utf-8')
        return self._load(json_text, request, full_keyspace)

    def _load(
            self,
            json_text: str,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        json_obj = json.loads(json_text)
        retval: dict[CfgFieldDesc, Any] = {}

        for namespace, field_tuples in full_keyspace.by_namespace.items():
            if namespace is None:
                target_toml_obj = json_obj
            else:
                target_toml_obj = json_obj.get(namespace, {})

            for field_desc, source in field_tuples:
                val = target_toml_obj.get(source.lookup_keys[0], _MISSING)
                if val is not _MISSING:
                    retval[field_desc] = val

        return retval


class _Missing(Enum):
    MISSING = 'missing'
_MISSING = _Missing.MISSING
