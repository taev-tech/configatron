from __future__ import annotations

import typing
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from docnote import ClcNote

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance
else:
    DataclassInstance = object


class InterfaceAnnotationFlavor(Enum):
    SECRET = 'secret'  # noqa: S105


@dataclass(frozen=True)
class InterfaceAnnotation:
    flavor: InterfaceAnnotationFlavor


# Technically this should be an intersection type with both the
# _ConfigIntersectable and the DataclassInstance returned by
# the dataclass transform. Unfortunately, type intersections don't yet exist in
# python, so we have to resort to this (overly broad) type
ConfigInstance = DataclassInstance
type ConfigClass = type[ConfigInstance]


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
