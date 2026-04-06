from typing import Protocol
from unittest.mock import patch

import pytest
from dcei import ext_dataclass

from configatron._registry import CfgRegistryState
from configatron._registry import NormalizedCfgCls
from configatron._registry import normalize_config_cls
from configatron.cfg_abstract import CfgMeta
from configatron.cfg_concrete import Configatron
from configatron.exceptions import MissingConcreteConfigs


class TestRegistryState:

    # Note: we're patching this out so that we can test the results directly
    # by calling, instead of relying on the call chain. It's maybe a bit
    # awkward, but it gets us better test isolation.
    @patch(
        'configatron.cfg_abstract.register_abstract_config_cls', autospec=True)
    @patch(
        'configatron.cfg_concrete.register_concrete_config_cls', autospec=True)
    def test_register_abstract(
            self,
            register_abstract_cfg_patch,
            register_concrete_cfg_patch,
            clean_single_config_registry: CfgRegistryState):
        """Registering an abstract class must simply add it to the
        abstract registry.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        regstate = clean_single_config_registry
        assert not regstate.abstract_cfg_classes
        assert not regstate.concrete_cfg_classes
        assert not regstate.concrete_lookup
        assert not regstate.abstract_lookup
        assert not regstate.concrete_by_namespace

        regstate.register_abstract(FakeConfig)
        assert regstate.abstract_cfg_classes == {FakeConfig}
        assert not regstate.concrete_cfg_classes
        assert not regstate.concrete_lookup
        assert not regstate.abstract_lookup
        assert not regstate.concrete_by_namespace

    # Note: we're patching this out so that we can test the results directly
    # by calling, instead of relying on the call chain. It's maybe a bit
    # awkward, but it gets us better test isolation.
    @patch(
        'configatron.cfg_abstract.register_abstract_config_cls', autospec=True)
    @patch(
        'configatron.cfg_concrete.register_concrete_config_cls', autospec=True)
    def test_register_concrete(
            self,
            register_abstract_cfg_patch,
            register_concrete_cfg_patch,
            clean_single_config_registry: CfgRegistryState):
        """Registering a concrete class must add it to the
        concrete registry and update its associated abstract class
        registration.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            ...

        regstate = clean_single_config_registry
        assert not regstate.abstract_cfg_classes
        assert not regstate.concrete_cfg_classes
        assert not regstate.concrete_lookup
        assert not regstate.abstract_lookup
        assert not regstate.concrete_by_namespace

        regstate.register_abstract(FakeConfig)
        assert regstate.abstract_cfg_classes == {FakeConfig}
        assert not regstate.concrete_cfg_classes
        assert not regstate.concrete_lookup
        assert not regstate.abstract_lookup
        assert not regstate.concrete_by_namespace

        regstate.register_concrete(FakeConfigImplementation)
        assert regstate.abstract_cfg_classes == {FakeConfig}
        assert regstate.concrete_cfg_classes == {FakeConfigImplementation}
        assert regstate.concrete_lookup[FakeConfig] is FakeConfigImplementation
        assert regstate.abstract_lookup[FakeConfigImplementation] is FakeConfig
        assert regstate.concrete_by_namespace['foo'] \
            is FakeConfigImplementation

    # Note: we're patching this out so that we can test the results directly
    # by calling, instead of relying on the call chain. It's maybe a bit
    # awkward, but it gets us better test isolation.
    @patch(
        'configatron.cfg_abstract.register_abstract_config_cls', autospec=True)
    @patch(
        'configatron.cfg_concrete.register_concrete_config_cls', autospec=True)
    def test_verify_completeness(
            self,
            register_abstract_cfg_patch,
            register_concrete_cfg_patch,
            clean_single_config_registry: CfgRegistryState):
        """Completion checking should fail before a concrete config is
        registered, but succeed afterwards.
        """
        class FakeConfig(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation(FakeConfig):
            ...

        regstate = clean_single_config_registry

        regstate.register_abstract(FakeConfig)

        with pytest.raises(MissingConcreteConfigs):
            regstate.verify_completeness()

        regstate.register_concrete(FakeConfigImplementation)
        assert regstate.verify_completeness()


class TestNormalizeConfigCls:

    def test_abstract_config(
            self,
            clean_single_config_registry):
        """Normalizing on an abstract config must return the abstract
        config and its concrete implementation, including in the
        presence of other configs.
        """
        class FakeConfig1(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation1(FakeConfig1):
            ...

        class FakeConfig2(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='bar'), slots=True)
        class FakeConfigImplementation2(FakeConfig2):
            ...

        retval = normalize_config_cls(FakeConfig1)

        assert isinstance(retval, NormalizedCfgCls)
        assert retval.abstract_cls is FakeConfig1
        assert retval.concrete_cls is FakeConfigImplementation1

    def test_concrete_config(
            self,
            clean_single_config_registry):
        """Normalizing on a concrete config must return the concrete
        config and its abstract counterpart, including in the
        presence of other configs.
        """
        class FakeConfig1(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='foo'), slots=True)
        class FakeConfigImplementation1(FakeConfig1):
            ...

        class FakeConfig2(Protocol, metaclass=CfgMeta):
            ...

        @ext_dataclass(Configatron(namespace='bar'), slots=True)
        class FakeConfigImplementation2(FakeConfig2):
            ...

        retval = normalize_config_cls(FakeConfigImplementation2)

        assert isinstance(retval, NormalizedCfgCls)
        assert retval.abstract_cls is FakeConfig2
        assert retval.concrete_cls is FakeConfigImplementation2
