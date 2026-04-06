from __future__ import annotations

import typing
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from enum import Enum
from typing import Annotated
from typing import Any
from typing import ClassVar
from typing import Protocol
from typing import TypeGuard

from docnote import ClcNote
from docnote import Note

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from configatron.cfg_abstract import CfgMeta
    from configatron.cfg_concrete import Configatron
else:
    DataclassInstance = object


class InterfaceAnnotationFlavor(Enum):
    SECRET = 'secret'  # noqa: S105


@dataclass(frozen=True)
class InterfaceAnnotation:
    flavor: InterfaceAnnotationFlavor


# Technically this should be an intersection type with both the
# _CfgIntersectable and the DataclassInstance returned by
# the dataclass transform. Unfortunately, type intersections don't yet exist in
# python, so we have to resort to this (overly broad) type
CfgInstance = DataclassInstance
type CfgClass = type[CfgInstance]


type Secret[T] = Annotated[
    T,
    InterfaceAnnotation(InterfaceAnnotationFlavor.SECRET),
    ClcNote(
        '''A ``Secret`` parameter is just that: a value that must remain
        confidential. Use this for cryptographic secrets, API keys, etc.

        This affects which backends the value can be retrieved from;
        only backends supporting secret information will be checked for
        secrets.

        Secrets will also be sanitized from config reprs, instead
        displaying a placeholder of their real, at-runtime type (ie,
        the result of calling ``type(value)``.
        ''')]


class CfgInstanceIntersectable(Protocol):
    """We need (but don't have) a proper intersection type to make the
    configs fully valid, so we use this along with casts instead.
    """
    _configatron_cfg: ClassVar[Configatron]

    @staticmethod
    def get_configatron_cfg(
            cls_or_instance: CfgClsIntersectable | CfgInstanceIntersectable
            ) -> Configatron:
        return cls_or_instance._configatron_cfg

    @staticmethod
    def set_configatron_cfg(configatron_cls: type, cfg: Configatron):
        configatron_cls._configatron_cfg = cfg


type CfgClsIntersectable = type[CfgInstanceIntersectable]


def is_cfg_xable(obj: object) -> TypeGuard[CfgInstanceIntersectable]:
    return (
        not isinstance(obj, type)
        and getattr(obj, '_configatron_cfg', None) is not None)


def is_cfg_cls_xable(obj: object) -> TypeGuard[CfgClsIntersectable]:
    return (
        isinstance(obj, type)
        and getattr(obj, '_configatron_cfg', None) is not None)


class TypeCoercer[T](Protocol):

    def __call__(
            self,
            config_cls: type[T],
            value: Any,
            ) -> T:
        """Type coercers are a callable that takes an input value and
        the desired config class, and performs any necessary type
        coercion to arrive at the correct config type.

        Practically speaking, this is included as a general-purpose
        extension mechanism, allowing eg pydantic to be used with
        configatron classes.
        """
        ...


@dataclass(slots=True, frozen=True)
class CfgSource:
    backend: Annotated[
            str | None,
            Note('''The name of the backend being configured. Set to ``None``
                to check all backends under the same lookup keys (this is
                also the default behavior if no config source is specified --
                in that case, the fieldname will be inferred as the only
                lookup key).''')]
    lookup_keys: Annotated[
            Sequence[str],
            Note('''An ordered tuple of possible lookup keys for the field.
                Earlier items should be searched first (ie, ``[0]`` before
                ``[1]``, etc).''')]
    metadata: Annotated[
            dict[str, Any],
            Note('''Any additional metadata required by the backend to load
                the config value.''')
        ] = field(default_factory=dict, compare=False)


@dataclass(slots=True, frozen=True)
class CfgFieldDesc:
    cfg_cls: Annotated[
            CfgMeta,
            Note('''The concrete config class that contains the field. This
                is primarily included as a convenience to the config manager
                for use when processing the return value of field loading,
                but it may also be useful if, for whatever reason, the loading
                backend needs access to the underlying class.''')
        ] = field(compare=False, repr=False)
    namespace: str | None
    name: Annotated[str, Note('The attribute name from the config class')]


@dataclass(slots=True, init=False)
class CfgField:
    sources: tuple[CfgSource, ...]
    refresh_after_max: float | None

    def __init__(
            self,
            *sources: CfgSource,
            refresh_after_max: float | None = None):
        self.sources = sources
        self.refresh_after_max = refresh_after_max
