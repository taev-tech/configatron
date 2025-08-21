# ruff: noqa: S106, S105
import dataclasses
from unittest.mock import patch

import pytest

from configatron._runtime_state import RawLookupKey
from configatron.configatron_ import configatron
from configatron.configatron_ import ensure_complete_config
from configatron.configatron_ import get_keyspace
from configatron.configatron_ import secret
from configatron.configatron_ import unsecured
from configatron.exceptions import ConfigKeyNotFound
from configatron.exceptions import InvalidConfigatronDefinition


class TestConfigatronDefinition:
    """Tests related to defining the Configatron itself."""

    def test_definition(self):
        """Test the simplest case and make sure metadata is set etc.
        """
        @configatron(namespace='test_definition')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        config_fields = _get_config_attrs(TestConfig)
        assert 'test_secret' in config_fields
        assert 'test_unsecured' in config_fields

    def test_happycase_inferred_names(self):
        """Test the happy case with inferred names."""

        @configatron(namespace='test_happycase_inferred_names')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        assert (
            _get_metadata(TestConfig, 'test_secret').config_key
            == 'test_secret')

        assert (
            _get_metadata(TestConfig, 'test_unsecured').config_key
            == 'test_unsecured')

    def test_fails_with_duplicate_primary_keys(self):
        """Make sure a config with duplicate primary config keys is
        considered invalid.
        """
        with pytest.raises(InvalidConfigatronDefinition):
            @configatron(namespace='test_definition')
            class TestConfig:
                test_secret: str = secret(config_key='foo')
                test_unsecured: str = unsecured(config_key='foo')

    def test_fails_with_duplicate_alt_keys(self):
        """Make sure a config with duplicate alternate config keys is
        considered invalid.
        """
        with pytest.raises(InvalidConfigatronDefinition):
            @configatron(namespace='test_definition')
            class TestConfig:
                test_secret: str = secret(config_key='foo')
                test_unsecured: str = unsecured(
                    config_key='bar', alt_config_keys=['foo'])

        with pytest.raises(InvalidConfigatronDefinition):
            @configatron(namespace='test_definition_2')
            class TestConfig2:
                test_secret: str = secret(config_key='foo')
                test_unsecured: str = unsecured(
                    config_key='bar', alt_config_keys=['oops', 'not', 'foo'])


def _make_fake_get_loaded_config(**config_items):
    def fake_get_loaded_config(namespace):
        fake_config = {}

        for config_name, config_value in config_items.items():
            key = RawLookupKey(namespace=namespace, name=config_name)
            fake_config[key] = config_value

        return fake_config

    return fake_get_loaded_config


class TestConfigatronAccess:
    """Tests related to accessing values within the Configatron, *after*
    it has been loaded successfully.
    """

    def test_instance_access(self):
        """Test that you can still access the actual vaues stored on the
        instance.
        """
        @configatron(namespace='test_instance_access')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        test_config = TestConfig(test_secret='foo', test_unsecured='bar')  # type: ignore

        assert test_config.test_secret == 'foo'
        assert test_config.test_unsecured == 'bar'

    @patch(
        'configatron.configatron_.get_loaded_config',
        _make_fake_get_loaded_config(test_secret='foo', test_unsecured='bar'))
    def test_class_access_simple(self):
        """Make sure that the happy case access on the class succeeds.
        """
        @configatron(namespace='test_class_access')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        assert TestConfig.test_secret == 'foo'
        assert TestConfig.test_unsecured == 'bar'

    @patch(
        'configatron.configatron_.get_loaded_config',
        _make_fake_get_loaded_config(foo='foo', bar='bar'))
    def test_class_access_aliased(self):
        """Make sure that the happy case access on the class succeeds
        with explicit config keys.
        """
        @configatron(namespace='test_class_access')
        class TestConfig:
            test_secret: str = secret(config_key='foo')
            test_unsecured: str = unsecured(config_key='bar')

        assert TestConfig.test_secret == 'foo'
        assert TestConfig.test_unsecured == 'bar'

    @patch(
        'configatron.configatron_.get_loaded_config',
        _make_fake_get_loaded_config(foo='foo', not_bar='bar'))
    def test_class_access_from_alt(self):
        """Make sure that the happy case access on the class succeeds
        with explicit config keys.
        """
        @configatron(namespace='test_class_access')
        class TestConfig:
            test_secret: str = secret(config_key='foo')
            test_unsecured: str = unsecured(
                config_key='bar', alt_config_keys=['oops', 'not_bar'])

        assert TestConfig.test_secret == 'foo'
        assert TestConfig.test_unsecured == 'bar'


def _get_config_attrs(cls):
    fields = dataclasses.fields(cls)
    return {field.name for field in fields}


def _get_metadata(cls, field_name):
    fields = {field.name: field for field in dataclasses.fields(cls)}
    field = fields[field_name]
    return field.metadata['configatron']


class TestGetKeyspace:

    def test_keyspace_for_secret(self):
        @configatron(namespace='test_keyspace_for_secret')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        class FakeBackend:
            allow_secret = True
            allow_unsecured = False

        keyspace = list(get_keyspace(FakeBackend))
        assert len(keyspace) == 1
        key, = keyspace
        assert key.name == 'test_secret'

    def test_keyspace_for_unsecured(self):
        @configatron(namespace='test_keyspace_for_unsecured')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        class FakeBackend:
            allow_secret = False
            allow_unsecured = True

        keyspace = list(get_keyspace(FakeBackend))
        assert len(keyspace) == 1
        key, = keyspace
        assert key.name == 'test_unsecured'

    def test_keyspace_for_both(self):
        @configatron(namespace='test_keyspace_for_both')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        class FakeBackend:
            allow_secret = True
            allow_unsecured = True

        keyspace = list(get_keyspace(FakeBackend))
        assert len(keyspace) == 2
        key_names = {key.name for key in keyspace}
        assert 'test_secret' in key_names
        assert 'test_unsecured' in key_names


class TestEnsureCompleteConfig:

    def test_happy_case_single_config(self):
        @configatron(namespace='testconfig')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        fake_lookup = {
            RawLookupKey('testconfig', 'test_secret'): 'foo',
            RawLookupKey('testconfig', 'test_unsecured'): 'bar'
        }

        assert ensure_complete_config(fake_lookup)

    def test_happy_case_double_config(self):
        @configatron(namespace='testconfig1')
        class TestConfig1:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        @configatron(namespace='testconfig2')
        class TestConfig2:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        fake_lookup = {
            RawLookupKey('testconfig1', 'test_secret'): 'foo',
            RawLookupKey('testconfig1', 'test_unsecured'): 'bar',
            RawLookupKey('testconfig2', 'test_secret'): 'foo',
            RawLookupKey('testconfig2', 'test_unsecured'): 'bar',
        }

        assert ensure_complete_config(fake_lookup)

    def test_insufficient_single_config(self):
        @configatron(namespace='testconfig')
        class TestConfig:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        fake_lookup = {
            RawLookupKey('testconfig', 'test_secret'): 'foo'
        }

        with pytest.raises(ConfigKeyNotFound):
            ensure_complete_config(fake_lookup)

    def test_insufficient_double_config(self):
        @configatron(namespace='testconfig1')
        class TestConfig1:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        @configatron(namespace='testconfig2')
        class TestConfig2:
            test_secret: str = secret()
            test_unsecured: str = unsecured()

        fake_lookup = {
            RawLookupKey('testconfig1', 'test_secret'): 'foo',
            RawLookupKey('testconfig1', 'test_unsecured'): 'bar',
            RawLookupKey('testconfig2', 'test_secret'): 'foo',
        }

        with pytest.raises(ConfigKeyNotFound):
            ensure_complete_config(fake_lookup)
