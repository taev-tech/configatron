import os
import re

COERCER = re.compile(r'[^A-z0-9_]')


class EnvVarBackend:
    """A config backend that uses environment variables for storage.
    Supports both secret and unsecured values. Note that modern best
    practices would prefer a more secure solution, for example, a
    third-party secrets manager.

    Namespaces are interpreted as prefixes to the environment variable
    key -- so for example ``namespace.foo`` would be converted to
    NAMESPACE_FOO.

    Note that we will also coalesce special characters within the
    namespace. Allowed characters are: [a-zA-Z0-9_]; anything else will
    be converted to an underscore.

    Many platforms don't support environment variables starting with
    numbers. If they're there, we'll load them successfully, but you
    may not be able to set them.
    """

    allow_secret = True
    allow_unsecured = True

    def load(self, keyspace):
        expected_keys = {}

        for key in keyspace:
            env_key = COERCER.sub('_', f'{key.namespace}_{key.name}'.upper())
            expected_keys[env_key] = key

        found_values = {}
        for env_key, value in os.environ.items():
            if env_key in expected_keys:
                found_values[expected_keys[env_key]] = value

        return found_values
