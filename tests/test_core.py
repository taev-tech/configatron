import dataclasses

from configatron import (
    configatron,
    secret,
    unsecured)


class TestConfigatronDefinition:

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
        """Test he happy case with inferred names."""

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


def _get_config_attrs(cls):
    fields = dataclasses.fields(cls)
    return {field.name for field in fields}


def _get_metadata(cls, field_name):
    fields = {field.name: field for field in dataclasses.fields(cls)}
    field = fields[field_name]
    return field.metadata['configatron']
