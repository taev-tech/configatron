import os


class EnvVarBackend:
    """A config backend that uses environment variables for storage.
    Supports both secret and unsecured values. Note that modern best
    practices would prefer a more secure solution, for example, a
    third-party secrets manager.

    Namespaces are interpreted as prefixes to the environment variable
    key -- so for example ``namespace.foo`` would be converted to
    NAMESPACE_FOO.
    """

    allow_secret = True
    allow_unsecured = True

    def load(self, keyspace):
        expected_keys = {}

        for key in keyspace:
            env_key = f'{key.namespace}_{key.name}'.upper()
            expected_keys[env_key] = key

        found_values = {}
        for env_key, value in os.environ.items():
            if env_key in expected_keys:
                found_values[expected_keys[env_key]] = value

        return found_values
