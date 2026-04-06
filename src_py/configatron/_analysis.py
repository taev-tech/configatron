from __future__ import annotations

import typing
from dataclasses import dataclass
from dataclasses import fields
from typing import Annotated
from typing import cast
from typing import get_origin as get_type_origin
from typing import get_type_hints

from docnote import Note

from configatron._registry import NormalizedCfgCls
from configatron.exceptions import MissingAbstractFields
from configatron.types import CfgField
from configatron.types import CfgFieldDesc
from configatron.types import CfgSource
from configatron.types import Secret

if typing.TYPE_CHECKING:
    from _typeshed import DataclassInstance

else:
    # We need this to be defined for a cast call, but otherwise it's unused
    DataclassInstance = object


@dataclass(slots=True)
class FieldAnalysis:
    field_desc: CfgFieldDesc
    refresh_after_max: float | None
    is_secret: bool
    is_concrete_only: Annotated[
        bool,
        Note('''True if the field was only defined on the concrete config
            class, but missing from the abstract one.''')]
    sources: Annotated[
        tuple[CfgSource, ...],
        Note('''An ordered (by precedence) list of possible backends for the
            field, **before any backend-specific filtering is applied.**
            In other words, this does not take into account backends that
            are declared as secret-only or plaintext-only.''')]


def analyze_cfg_cls(
        namespace: str | None,
        norm_cfg_cls: NormalizedCfgCls
        ) -> tuple[FieldAnalysis, ...]:
    """Analyzes a normalized config class, extracting out the relevant
    configuration information for each field and storing it in an
    easily-accessible format.
    """
    abstract_annos = get_type_hints(norm_cfg_cls.abstract_cls)
    concrete_fields: dict[str, CfgField | None]  = {}
    concrete_annos = get_type_hints(norm_cfg_cls.concrete_cls)

    # First extract the sourcing information from the concrete class
    for dc_field in fields(cast(DataclassInstance, norm_cfg_cls.concrete_cls)):
        cfg_field: CfgField | None = dc_field.metadata.get(CfgField)
        concrete_fields[dc_field.name] = cfg_field

    # Now verify that all of the abstract fields are declared on the concrete
    # class. Note that we're permissive of extra fields on the concrete class;
    # as long as they can be loaded from the backend, it'll work. This can be
    # helpful if ex an application wants to add additional config info to an
    # imported library for its own internal application logic
    missing_abstract = set(abstract_annos) - set(concrete_fields)
    if missing_abstract:
        raise MissingAbstractFields(norm_cfg_cls, missing_abstract)

    # Now we check for any secret annotations on the abstract class, then on
    # the concrete one
    abs_is_secret: dict[str, bool] = {}
    for abstract_fieldname, anno in abstract_annos.items():
        anno_origin = get_type_origin(anno)
        if anno_origin is Secret:
            abs_is_secret[abstract_fieldname] = True
        else:
            abs_is_secret[abstract_fieldname] = False
    concrete_is_secret: dict[str, bool] = {}
    for concrete_fieldname, anno in concrete_annos.items():
        anno_origin = get_type_origin(anno)
        if anno_origin is Secret:
            concrete_is_secret[concrete_fieldname] = True
        else:
            concrete_is_secret[concrete_fieldname] = False

    # Finally, distill all of that into FieldAnalysis objects
    retval: list[FieldAnalysis] = []
    for fieldname, cfg_field in concrete_fields.items():
        if cfg_field is None:
            refresh_after_max = None
            sources = (CfgSource(None, (fieldname,)),)

        elif cfg_field.sources:
            refresh_after_max = cfg_field.refresh_after_max
            sources = cfg_field.sources

        else:
            refresh_after_max = cfg_field.refresh_after_max
            sources = (CfgSource(None, (fieldname,)),)

        retval.append(FieldAnalysis(
            field_desc=CfgFieldDesc(
                cfg_cls=norm_cfg_cls.concrete_cls,
                namespace=namespace,
                name=fieldname),
            refresh_after_max=refresh_after_max,
            is_secret=bool(
                abs_is_secret.get(fieldname)
                or concrete_is_secret.get(fieldname)),
            is_concrete_only=(fieldname not in abstract_annos),
            sources=sources))

    return tuple(retval)
