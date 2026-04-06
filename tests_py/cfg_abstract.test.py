from typing import Protocol
from typing import assert_type
from unittest.mock import patch

from configatron.cfg_abstract import CfgMeta


class TestConfigMeta:

    @patch('configatron.cfg_abstract.get_active_cfg', autospec=True)
    def test_shorthand_retrieval(
            self,
            get_active_cfg_patch,
            clean_single_config_registry):
        """Getting a config via the shorthand syntax must work as
        expected (and typecheck correctly).
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        retval = (~FakeConfig)

        assert_type(retval, FakeConfig)
        assert get_active_cfg_patch.call_count == 1
        assert retval is get_active_cfg_patch.return_value

    @patch(
        'configatron.cfg_abstract.register_abstract_config_cls', autospec=True)
    def test_registration(
            self,
            register_cfg_patch,
            clean_single_config_registry):
        """Creating an abstract config class must register it.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        assert register_cfg_patch.call_count == 1

    def test_configatron_classes(
            self,
            clean_single_config_registry):
        """Creating abstract classes (and subclasses) must correctly
        extract and record the configatron classes within the MRO.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        class FakeChildConfig(FakeConfig, Protocol):
            ...

        class FakeGrandchildConfig(FakeChildConfig):
            ...

        assert FakeConfig.__CONFIGATRON_CLASSES__ == (FakeConfig,)
        assert FakeChildConfig.__CONFIGATRON_CLASSES__ == (
            FakeChildConfig, FakeConfig)
        assert FakeGrandchildConfig.__CONFIGATRON_CLASSES__ == (
            FakeGrandchildConfig, FakeChildConfig, FakeConfig)
