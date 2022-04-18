import collections
import functools
import pathlib

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from configatron.exceptions import ConfigKeyNotFound
from configatron._runtime_state import RawLookupKey


class TomlBackend:

    allow_secret = False
    allow_unsecured = True

    def __init__(self, path):
        self._path = pathlib.Path(path)

    def load(self, keyspace):
        expected_namespaces = set()
        expected_keys = collections.defaultdict(set)

        for key in keyspace:
            expected_namespaces.add(key.namespace)
            expected_keys[key.namespace].add(key.name)

        with self._path.read('rb') as fd:
            raw_toml_dict = tomllib.load(fd)

        transformed_lookup = {}
        for namespace in expected_namespaces:
            if namespace in raw_toml_dict:
                raw_namespace_dict = raw_toml_dict[namespace]

                for raw_key in expected_keys[namespace]:
                    if raw_key in raw_namespace_dict:
                        key = RawLookupKey(namespace=namespace, name=raw_key)
                        transformed_lookup[key] = raw_namespace_dict[raw_key]

        return transformed_lookup


def extract_value(toml_dict, raw_lookup_key):
    """This is a utility function to extract a raw_lookup_key from the
    raw toml_dict. It's not currently used anywhere.
    """
    namespace_dict = toml_dict.get(raw_lookup_key.namespace)

    if namespace_dict is None:
        raise ConfigKeyNotFound(raw_lookup_key)

    value = namespace_dict.get(raw_lookup_key.name)
    # Toml doesn't support nulls, so there's no need to add a singleton for
    # detecting missing values
    if value is None:
        raise ConfigKeyNotFound(raw_lookup_key)

    return value
