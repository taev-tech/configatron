from typing import Protocol

from dcei import ext_dataclass

from configatron.cfg_abstract import CfgMeta
from configatron.cfg_concrete import Configatron
from configatron.manager import _ConfigCtx
from configatron.manager import get_active_cfg
from configatron.types import Secret


class TestGetActiveCfg:

    def test_abstract_config(
            self,
            clean_config_context: _ConfigCtx):
        """Calling ``get_active_cfg`` on the abstract config must
        return the concrete instance.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: Secret[str]

        active_config = FakeConfigImplementation(
            foo=1,
            bar='rab',
            baz='zab')
        clean_config_context[FakeConfigImplementation] = active_config

        retval = get_active_cfg(FakeConfig)

        assert retval is active_config

    def test_concrete_config(
            self,
            clean_config_context: _ConfigCtx):
        """Calling ``get_active_cfg`` on the concrete config must
        return the concrete instance.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            foo: int
            bar: str
            baz: Secret[str]

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            foo: int
            bar: str
            baz: Secret[str]

        active_config = FakeConfigImplementation(
            foo=1,
            bar='rab',
            baz='zab')
        clean_config_context[FakeConfigImplementation] = active_config

        retval = get_active_cfg(FakeConfigImplementation)

        assert retval is active_config
