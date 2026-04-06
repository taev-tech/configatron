from __future__ import annotations

from typing import Any
from typing import Protocol

from configatron._registry import register_abstract_config_cls
from configatron.manager import get_active_cfg


class CfgMeta(type(Protocol)):
    """The ``ConfigMeta`` class keeps track of all config types in its
    class' MROs. It also implements support for the shorthand config
    retrieval mechanism via the tilde unary operator, like this:

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
    __CONFIGATRON_CLASSES__: tuple[CfgMeta, ...]

    def __new__(
            metacls,
            cls_name: str,
            cls_bases: tuple[type],
            cls_namespace: dict[str, Any],
            /,
            **kwargs):
        return super().__new__(
            metacls, cls_name, cls_bases, cls_namespace, **kwargs)

    def __init__(
            cls,
            cls_name: str,
            cls_bases: tuple[type],
            cls_namespace: dict[str, Any],
            /,
            **kwargs):
        super().__init__(cls_name, cls_bases, cls_namespace, **kwargs)

        # This gets accessed by the dcei config finalizer on the concrete
        # class
        cfg_mro = tuple(
            parent for parent in cls.__mro__ if isinstance(parent, CfgMeta))
        cls.__CONFIGATRON_CLASSES__ = cfg_mro
        register_abstract_config_cls(cls)

    def __invert__[T](cls: type[T]) -> T:
        # TODO: this needs to fetch from the registry!
        return get_active_cfg(cls)
