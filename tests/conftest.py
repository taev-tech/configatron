from unittest.mock import patch

import pytest

from configatron.configatron_ import configatron
from configatron.configatron_ import secret
from configatron.configatron_ import unsecured


@pytest.fixture(autouse=True)
def clean_configatron_registry():
    with patch('configatron._runtime_state.ALL_CONFIGATRONS', {}):
        yield


@pytest.fixture
def sample_config(clean_configatron_registry):
    """Define a sample config for use. Depends on the clean configatron
    registry.
    """
    @configatron(namespace='sample_config')
    class TestConfig:
        one: str = secret(config_key='one')
        two: str = secret(config_key='two')
        three: str = unsecured(config_key='three')
        four: str = unsecured(config_key='four')

    return TestConfig


@pytest.fixture
def sample_config_only_unsecured(clean_configatron_registry):
    """Define a sample config for use. Depends on the clean configatron
    registry.
    """
    @configatron(namespace='sample_config_only_unsecured')
    class TestConfig:
        one: str = unsecured(config_key='one')
        two: str = unsecured(config_key='two')
        three: str = unsecured(config_key='three')
        four: str = unsecured(config_key='four')

    return TestConfig


@pytest.fixture
def sample_config_only_secret(clean_configatron_registry):
    """Define a sample config for use. Depends on the clean configatron
    registry.
    """
    @configatron(namespace='sample_config_only_secret')
    class TestConfig:
        one: str = secret(config_key='one')
        two: str = secret(config_key='two')
        three: str = secret(config_key='three')
        four: str = secret(config_key='four')

    return TestConfig
