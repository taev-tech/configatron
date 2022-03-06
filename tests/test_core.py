import dataclasses
from functools import partial
from unittest.mock import patch

import pytest

from configatron import (
    configatron,
    secret,
    unsecured)
from configatron._runtime_state import RawLookupKey
from configatron.exceptions import ConfigNotLoaded


class TestConfigatronDefinition:
    """Tests related to defining the Configatron itself."""

    def test_definition(self):
        """Test the simplest case and make sure metadata is set etc.
        """
        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        config_fields = _get_config_attrs(TestConfig)
        assert 'test_secret' in config_fields
        assert 'test_unsecured' in config_fields

    def test_happycase_inferred_names(self):
        """Test the happy case with inferred names."""

        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        assert (
            _get_metadata(TestConfig, 'test_secret').primary_name
            == 'test_secret')

        assert (
            _get_metadata(TestConfig, 'test_unsecured').primary_name
            == 'test_unsecured')


def _make_fake_loaded_config(backend, namespace, /, **config_items):
    fake_config = {}

    for config_name, config_value in config_items.items():
        key = RawLookupKey(
            backend=backend, namespace=namespace, name=config_name)
        fake_config[key] = config_value

    return fake_config


class TestConfigatronAccess:
    """Tests related to accessing values within the Configatron, *after*
    it has been loaded successfully.
    """

    def test_instance_access(self):
        """Test that you can still access the actual vaues stored on the
        instance.
        """
        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        test_config = TestConfig(test_secret='foo', test_unsecured='bar')

        assert test_config.test_secret == 'foo'
        assert test_config.test_unsecured == 'bar'

    @patch(
        'configatron.core.get_loaded_config',
        partial(
            _make_fake_loaded_config, None, 'test',
            test_secret='foo', test_unsecured='bar'))
    def test_class_access(self):
        """Make sure that the happy case access on the class succeeds.
        """
        @configatron(namespace='test')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        assert TestConfig.test_secret == 'foo'
        assert TestConfig.test_unsecured == 'bar'


def _get_config_attrs(cls):
    fields = dataclasses.fields(cls)
    return {field.name for field in fields}


def _get_metadata(cls, field_name):
    fields = {field.name: field for field in dataclasses.fields(cls)}
    field = fields[field_name]
    return field.metadata['configatron']
