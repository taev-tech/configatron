"""This maintains a registry of all defined config types. They are then
used by the config manager to analyze the configs and create their
signatures, as well as any required ser/de models.
"""
from __future__ import annotations

import typing
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from typing import Literal
from typing import cast

from configatron.exceptions import ConfigatronInternalError
from configatron.exceptions import DuplicateConfigNamespace
from configatron.exceptions import MissingConcreteConfigs
from configatron.exceptions import MultipleConcreteConfigsForAbstract
from configatron.types import CfgInstanceIntersectable
from configatron.types import is_cfg_cls_xable

if typing.TYPE_CHECKING:
    from configatron.cfg_abstract import CfgMeta
else:
    # We need this to be defined for a cast call, but otherwise it's unused
    CfgMeta = type


@dataclass(slots=True)
class CfgRegistryState:
    """Used as a mutable container for the registry state, keeping track
    of which concrete config classes correspond to which abstract ones.
    """
    abstract_cfg_classes: set[CfgMeta] = field(default_factory=set)
    concrete_cfg_classes: set[CfgMeta] = field(default_factory=set)

    concrete_lookup: dict[CfgMeta, CfgMeta] = field(default_factory=dict)
    abstract_lookup: dict[CfgMeta, CfgMeta] = field(default_factory=dict)

    concrete_by_namespace: dict[str | None, CfgMeta] = field(
        default_factory=dict)

    def register_abstract(self, cfg_cls: CfgMeta):
        """Call this when creating/finalizing an abstract config class
        to add it to the registry.
        """
        self.abstract_cfg_classes.add(cfg_cls)

    def register_concrete(self, cfg_cls: CfgMeta):
        """Call this when creating/finalizing a concrete config class
        to add it to the registry.
        """
        if cfg_cls in self.abstract_lookup:
            raise MultipleConcreteConfigsForAbstract(cfg_cls)

        cfg_cls_xable = cfg_cls
        if not is_cfg_cls_xable(cfg_cls_xable):
            raise TypeError('Not a concrete config!', cfg_cls)

        configatron_cfg = CfgInstanceIntersectable.get_configatron_cfg(
            cfg_cls_xable)
        if configatron_cfg.namespace in self.concrete_by_namespace:
            raise DuplicateConfigNamespace(cfg_cls, configatron_cfg.namespace)

        self.concrete_cfg_classes.add(cfg_cls)
        self.concrete_by_namespace[configatron_cfg.namespace] = cfg_cls

        parent_cfg_classes = cfg_cls.__CONFIGATRON_CLASSES__
        # This is a concrete class with no abstract parents. Therefore, it must
        # be both -- ie, it's an application config.
        if len(parent_cfg_classes) == 1:
            mro_cfg_cls, = parent_cfg_classes
            if mro_cfg_cls is not cfg_cls:
                raise ConfigatronInternalError(
                    'Impossible branch: cfg class not in its own MRO', cfg_cls)
            abstract_cfg_cls = cfg_cls

        else:
            *_, abstract_cfg_cls = parent_cfg_classes

        self.concrete_lookup[abstract_cfg_cls] = cfg_cls
        self.abstract_lookup[cfg_cls] = abstract_cfg_cls

    def verify_completeness(self) -> Literal[True]:
        """Returns True if a concrete config class has been declared for
        every abstract config. Otherwise, raises
        ``MissingConcreteConfigs``.
        """
        missing = self.abstract_cfg_classes - set(self.concrete_lookup)
        if missing:
            raise MissingConcreteConfigs(
                'Missing concrete ``Configatron`` implementation classes for '
                + 'abstract config(s)', missing)

        return True


_CONFIG_REGISTRY: ContextVar[CfgRegistryState] = ContextVar(
    '_CONFIG_REGISTRY', default=CfgRegistryState())  # noqa: B039


@contextmanager
def create_registry_context() -> Generator[CfgRegistryState, None, None]:
    """Call this if you need to create a separate registry context. This
    is only intended for use within configatron's own testing.
    """
    registry_state = CfgRegistryState()
    ctx_token = _CONFIG_REGISTRY.set(registry_state)
    try:
        yield registry_state
    finally:
        _CONFIG_REGISTRY.reset(ctx_token)


def register_abstract_config_cls(cfg_cls: CfgMeta):
    """Call this to finalize an abstract config class (which might also
    be a concrete config class), as the last step in processing the
    config class (via its metaclass).
    """
    registry = _CONFIG_REGISTRY.get()
    registry.register_abstract(cfg_cls)


def register_concrete_config_cls(cfg_cls: CfgMeta):
    """Call this to finalize a concrete config class, as the last step
    in DCEI postprocessing.
    """
    registry = _CONFIG_REGISTRY.get()
    registry.register_concrete(cfg_cls)


@dataclass(slots=True)
class NormalizedCfgCls:
    abstract_cls: CfgMeta
    concrete_cls: CfgMeta


def normalize_config_cls(cfg_cls: CfgMeta) -> NormalizedCfgCls:
    """Given a config class -- either abstract or concrete --
    normalizes it to a NormalizedCfgCls object, containing both the
    abstract **and** concrete config classes.
    """
    registry = _CONFIG_REGISTRY.get()

    if is_cfg_cls_xable(cfg_cls):
        concrete = cast(CfgMeta, cfg_cls)
        abstract = registry.abstract_lookup[concrete]
    else:
        concrete = registry.concrete_lookup[cfg_cls]
        abstract = cfg_cls

    return NormalizedCfgCls(abstract, concrete)
