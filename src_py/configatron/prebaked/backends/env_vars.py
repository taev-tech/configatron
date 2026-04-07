from __future__ import annotations

import os
import re
import typing
from typing import Any

from configatron.backends import CfgBackend
from configatron.backends import KeyspaceSummary
from configatron.types import CfgFieldDesc

try:
    import anyio
except ImportError:
    if typing.TYPE_CHECKING:
        import anyio

NAME_COERCER = re.compile(r'[^A-z0-9_]')


class EnvVarBackend(CfgBackend):
    """A config backend that uses environment variables for storage.
    Supports both secret and unsecured values. Note that modern best
    practices would prefer a more secure solution, for example, a
    third-party secrets manager.

    This will always check the first (and only the first) lookup key in
    the config sources.

    Namespaces are interpreted as prefixes to the environment variable
    key -- so for example ``my_namespace -> foo`` would be converted to
    MY_NAMESPACE_FOO.

    Note that we will also coalesce special characters within the
    namespace. Allowed characters are: [a-zA-Z0-9_]; anything else will
    be converted to an underscore.

    Many platforms don't support environment variables starting with
    numbers. If they're there, we'll load them successfully, but you
    may not be able to set them.
    """
    ALLOW_SECRET = True
    ALLOW_PLAINTEXT = True

    def load_sync(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        expected_keys: dict[str, CfgFieldDesc] = {}

        for field_desc, field_src in full_keyspace.flattened:
            expected_keys[NAME_COERCER.sub(
                '_',
                f'{field_desc.namespace}_{field_src.lookup_keys[0]}'.upper())
            ] = field_desc

        loadable_vars = set(os.environ)
        loadable_vars.difference_update(expected_keys.values())
        return {
            expected_keys[varname]: os.environ[varname]
            for varname in loadable_vars}

    async def load_async(
            self,
            request: KeyspaceSummary,
            full_keyspace: KeyspaceSummary
            ) -> dict[CfgFieldDesc, Any]:
        await anyio.sleep(0)
        return self.load_sync(request, full_keyspace)
