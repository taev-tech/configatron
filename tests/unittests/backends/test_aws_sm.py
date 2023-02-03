"""Test the keyring backend. Note that this is a liiiittle bit awkward
(in that we actually manipulate the keyring instead of mocking it out),
but we do this so that we can actually integration test the library on
the supported platforms.
"""
import boto3
import pytest
from moto import mock_secretsmanager

from configatron.backends.aws_sm import AWSSecretsManagerBackend
from configatron.configatron_loader import ConfigatronLoader

CONFIG_KEYS = [
    ('sample_config_only_secret', 'one', 'one'),
    ('sample_config_only_secret', 'two', 'two'),
    ('sample_config_only_secret', 'three', 'three'),
    ('sample_config_only_secret', 'four', 'four'),
]


@pytest.fixture
def populate_secrets():
    with mock_secretsmanager():
        session = boto3.session.Session(region_name='us-west-2')
        client = session.client(service_name='secretsmanager')

        for namespace, key, value in CONFIG_KEYS:
            client.create_secret(
                Name=f'{namespace}/{key}',
                SecretString=value)

        yield


def test_loading(sample_config_only_secret, populate_secrets):
    backend = AWSSecretsManagerBackend(
        boto3_session_kwargs={'region_name': 'us-west-2'})
    loader = ConfigatronLoader([backend])

    with loader.load():
        assert sample_config_only_secret.one == 'one'
        assert sample_config_only_secret.two == 'two'
        assert sample_config_only_secret.three == 'three'
        assert sample_config_only_secret.four == 'four'
