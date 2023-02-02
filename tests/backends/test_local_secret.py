"""Test the keyring backend. Note that this is a liiiittle bit awkward
(in that we actually manipulate the keyring instead of mocking it out),
but we do this so that we can actually integration test the library on
the supported platforms.
"""
import keyring
import pytest

from configatron.backends.local_secret import LocalSecretBackend
from configatron.configatron_loader import ConfigatronLoader

CONFIG_KEYS = [
    ('sample_config_only_secret', 'one', 'one'),
    ('sample_config_only_secret', 'two', 'two'),
    ('sample_config_only_secret', 'three', 'three'),
    ('sample_config_only_secret', 'four', 'four'),
]


@pytest.fixture
def populate_local_secrets():
    for namespace, key, value in CONFIG_KEYS:
        keyring.set_password(namespace, key, value)

    try:
        yield
    finally:
        for namespace, key, __ in CONFIG_KEYS:
            keyring.delete_password(namespace, key)


def test_loading(sample_config_only_secret, populate_local_secrets):
    backend = LocalSecretBackend()
    loader = ConfigatronLoader([backend])

    with loader.load():
        assert sample_config_only_secret.one == 'one'
        assert sample_config_only_secret.two == 'two'
        assert sample_config_only_secret.three == 'three'
        assert sample_config_only_secret.four == 'four'
