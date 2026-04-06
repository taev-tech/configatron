from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import TypeGuard

from dcei import DataclassKwargs
from dcei import DceiClassConfigDict
from dcei import DceiConfigProtocol

from configatron._registry import register_concrete_config_cls
from configatron.cfg_abstract import CfgMeta
from configatron.types import CfgClsIntersectable
from configatron.types import CfgInstanceIntersectable

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance


@dataclass(slots=True)
class Configatron(DceiConfigProtocol):
    """``Configatron`` instances represent a concrete config
    implementation, including all of the necessary information required
    to load config fields from backends.
    """
    namespace: str | None

    def postprocess_dataclass(
            self,
            cls: type[DataclassInstance],
            cls_configs: DceiClassConfigDict,
            dataclass_kwargs: DataclassKwargs
            ) -> TypeGuard[type[CfgClsIntersectable]]:
        if not isinstance(cls, CfgMeta):
            raise TypeError(
                'Concrete config class must use CfgMeta metaclass!', cls)

        configatron = cls_configs[Configatron]
        CfgInstanceIntersectable.set_configatron_cfg(cls, configatron)
        register_concrete_config_cls(cls)

        return True
