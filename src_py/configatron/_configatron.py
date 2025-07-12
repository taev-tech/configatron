from __future__ import annotations

import functools
import sys
from collections.abc import Callable
from collections.abc import Sequence
from collections.abc import Mapping
from dataclasses import _MISSING_TYPE
from dataclasses import Field
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from typing import Annotated
from typing import Any
from typing import Literal
from typing import dataclass_transform
from typing import overload


# The following is adapted directly from typeshed. We did some formatting
# updates, and inserted our prerenderer param.
if sys.version_info >= (3, 14):
    @overload
    def cfg_field[_T](
            *,
            default: _T,
            default_factory: Literal[_MISSING_TYPE.MISSING] = ...,
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            compare: bool = True,
            metadata: Mapping[Any, Any] | None = None,
            kw_only: bool | Literal[_MISSING_TYPE.MISSING] = ...,
            doc: str | None = None,
            backends: Sequence[str] | None = None,
            lookup_keys: Sequence[str] | None = None,
            refresh_after_max: float = float('inf'),
            ) -> _T: ...
    @overload
    def cfg_field[_T](
            *,
            default: Literal[_MISSING_TYPE.MISSING] = ...,
            default_factory: Callable[[], _T],
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            compare: bool = True,
            metadata: Mapping[Any, Any] | None = None,
            kw_only: bool | Literal[_MISSING_TYPE.MISSING] = ...,
            doc: str | None = None,
            backends: Sequence[str] | None = None,
            lookup_keys: Sequence[str] | None = None,
            refresh_after_max: float = float('inf'),
            ) -> _T: ...
    @overload
    def cfg_field[_T](
            *,
            default: Literal[_MISSING_TYPE.MISSING] = ...,
            default_factory: Literal[_MISSING_TYPE.MISSING] = ...,
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            compare: bool = True,
            metadata: Mapping[Any, Any] | None = None,
            kw_only: bool | Literal[_MISSING_TYPE.MISSING] = ...,
            doc: str | None = None,
            backends: Sequence[str] | None = None,
            lookup_keys: Sequence[str] | None = None,
            refresh_after_max: float = float('inf'),
            ) -> Any: ...

# This is technically only valid for >=3.10, but we require that anyways
else:
    @overload
    def cfg_field[_T](
            *,
            default: _T,
            default_factory: Literal[_MISSING_TYPE.MISSING] = ...,
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            compare: bool = True,
            metadata: Mapping[Any, Any] | None = None,
            kw_only: bool | Literal[_MISSING_TYPE.MISSING] = ...,
            backends: Sequence[str] | None = None,
            lookup_keys: Sequence[str] | None = None,
            refresh_after_max: float = float('inf'),
            ) -> _T: ...
    @overload
    def cfg_field[_T](
            *,
            default: Literal[_MISSING_TYPE.MISSING] = ...,
            default_factory: Callable[[], _T],
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            compare: bool = True,
            metadata: Mapping[Any, Any] | None = None,
            kw_only: bool | Literal[_MISSING_TYPE.MISSING] = ...,
            backends: Sequence[str] | None = None,
            lookup_keys: Sequence[str] | None = None,
            refresh_after_max: float = float('inf'),
            ) -> _T: ...
    @overload
    def cfg_field[_T](
            *,
            default: Literal[_MISSING_TYPE.MISSING] = ...,
            default_factory: Literal[_MISSING_TYPE.MISSING] = ...,
            init: bool = True,
            repr: bool = True,
            hash: bool | None = None,
            compare: bool = True,
            metadata: Mapping[Any, Any] | None = None,
            kw_only: bool | Literal[_MISSING_TYPE.MISSING] = ...,
            backends: Sequence[str] | None = None,
            lookup_keys: Sequence[str] | None = None,
            refresh_after_max: float = float('inf'),
            ) -> Any: ...


def cfg_field(
        *,
        backends: Sequence[str] | None = None,
        lookup_keys: Sequence[str] | None = None,
        refresh_after_max: float = float('inf'),
        metadata: Mapping[Any, Any] | None = None,
        **field_kwargs):
    inserted_metadata = {
        # Copy these into tuples to protect against accidental mutation
        'configatron.backends':
            tuple(backends) if backends is not None else None,
        'configatron.lookup_keys':
            tuple(lookup_keys) if lookup_keys is not None else None,
        'configatron.refresh_after_max': refresh_after_max}

    if metadata is None:
        metadata = inserted_metadata
    else:
        metadata = {**metadata, **inserted_metadata}

    return field(**field_kwargs, metadata=metadata)


@dataclass_transform(
        field_specifiers=(cfg_field, field, Field),
        slots_default=True,
        kw_only_default=True)
def config[T: type](  # noqa: PLR0913
        namespace: str,
        *,
        init: bool = True,
        repr: bool = True,  # noqa: A002
        eq: bool = True,
        order: bool = False,
        unsafe_hash: bool = False,
        frozen: bool = False,
        match_args: bool = True,
        slots: bool = True,
        weakref_slot: bool = False
        ) -> Callable[[T], T]:
    """This both transforms the decorated class into a stdlib dataclass
    and declares it as a configatron class.

    **Note that unlike the stdlib dataclass decorator, this defaults to
    ``slots=True``.** If you find yourself having problems with
    metaclasses and/or subclassing, you can disable this by passing
    ``slots=False``. Generally speaking, though, this provides a
    free performance benefit. **If weakref support is required, be sure
    to pass ``weakref_slot=True``.
    """
    return functools.partial(
        make_config,
        dataclass_kwargs={
            'init': init,
            'repr': repr,
            'eq': eq,
            'order': order,
            'unsafe_hash': unsafe_hash,
            'frozen': frozen,
            'match_args': match_args,
            'slots': slots,
            'weakref_slot': weakref_slot
        },
        namespace=namespace)


def make_config[T: type](
        cls: T,
        *,
        namespace: str,
        dataclass_kwargs: dict[str, bool],
        ) -> T:
    """Programmatically creates a config class. Converts the class into
    a dataclass, passing along ``dataclass_kwargs`` to the dataclass
    constructor (note: ``kw_only`` is always true, and declaring it will
    result in an error). Finally, registers it in the global config
    registry, so it can be loaded automatically by the config manager.
    """
    if 'kw_only' in dataclass_kwargs:
        raise ValueError(
            'Configatron classes are always kw_only. This param cannot '
            + 'be specified.')

    # These must always be keyword-only for subclassing to be sane
    # when overriding ``cfg_field`` params
    cls = dataclass(**dataclass_kwargs, kw_only=True)(cls)
    return cls


class ConfigMeta(type):
    """Optionally, use this metaclass to support the shorthand retrieval
    of config values via the tilde unary operator, like this:

    > Example shorthand access via metaclass
    __embed__: 'code/python'
        from configatron import ConfigMeta
        from configatron import configatron


        @configatron('my_namespace')
        class MyConfig(metaclass=ConfigMeta)
            foo: str


        def my_application_code():
            foo = (~MyConfig).foo
            ...
    """

    def __invert__[T](self: type[T]) -> T:
        # TODO: this needs to fetch from the registry!
        return self()
