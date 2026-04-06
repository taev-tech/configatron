from typing import Protocol
from typing import cast
from unittest.mock import patch

import pytest
from dcei import ext_dataclass

from configatron.cfg_abstract import CfgMeta
from configatron.cfg_concrete import Configatron
from configatron.types import CfgClsIntersectable
from configatron.types import CfgInstanceIntersectable


class TestConfigatron:

    @patch(
        'configatron.cfg_concrete.register_concrete_config_cls', autospec=True)
    def test_registration(
            self,
            register_cfg_patch,
            clean_single_config_registry):
        """Creating a concrete config class must register it.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='foo'))
        class FakeConfigImplementation(FakeConfig):
            ...

        assert register_cfg_patch.call_count == 1

    def test_configatron_classes(
            self,
            clean_single_config_registry):
        """The implementation class must also have a correct set of
        __CONFIGATRON_CLASSES__, even if it uses slots.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            ...

        assert FakeConfigImplementation.__CONFIGATRON_CLASSES__ == (
            FakeConfigImplementation, FakeConfig,)

    def test_configatron_set(
            self,
            clean_single_config_registry):
        """The configatron cfg must be set on the implementation class
        after it's been processed (but not the abstract class).
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        configatron_cfg = Configatron(namespace='foo')
        @ext_dataclass(configatron_cfg, slots=True)
        class FakeConfigImplementation(FakeConfig):
            ...

        with pytest.raises(AttributeError):
            CfgInstanceIntersectable.get_configatron_cfg(FakeConfig)  # type: ignore

        check_configatron_cfg = CfgInstanceIntersectable.get_configatron_cfg(
            cast(CfgClsIntersectable, FakeConfigImplementation))

        assert check_configatron_cfg is configatron_cfg
