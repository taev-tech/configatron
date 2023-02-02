import keyring


class LocalSecretBackend:
    """A config backend that uses the keyring library for storage. That
    means on OSX you'll use the keychain, on windows the credential
    locker, and on linux... well, linux gets complicated; see the
    keyring docs. At any rate, the main point is: this secret store is
    located on the current system, and not available over the network.

    Note that it's not possible to store None values as such, because
    keyring will return None for missing values. Instead, store them as
    empty strings.
    """

    allow_secret = True
    allow_unsecured = False

    def load(self, keyspace):
        found_values = {}

        # Keyring doesn't give us a way to explore the whole keyspace, so...
        # just check every possible secret, I guess
        for key in keyspace:
            maybe_secret = keyring.get_password(key.namespace, key.name)
            if maybe_secret is not None:
                found_values[key] = maybe_secret

        return found_values
