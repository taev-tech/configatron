from __future__ import annotations

import logging
import typing
from collections import defaultdict
from collections.abc import Generator
from collections.abc import Mapping
from contextlib import asynccontextmanager
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from dataclasses import fields
from enum import Enum
from types import MappingProxyType
from typing import Annotated
from typing import Any
from typing import cast

from docnote import DocnoteConfig
from docnote import Note
from docnote import docnote

from configatron._analysis import CfgAnalysis
from configatron._analysis import analyze_cfg_cls
from configatron._registry import normalize_config_cls
from configatron.backends import CfgBackend
from configatron.backends import KeyspaceSummary
from configatron.exceptions import ConfigNotLoaded
from configatron.types import CfgClsIntersectable
from configatron.types import CfgFieldDesc
from configatron.types import CfgInstanceIntersectable
from configatron.types import CfgSource
from configatron.types import TypeCoercer

if typing.TYPE_CHECKING:
    from configatron.cfg_abstract import CfgMeta
else:
    # We need this to be defined for a cast call, but otherwise it's unused
    CfgMeta = type

try:
    import anyio
except ImportError:
    if typing.TYPE_CHECKING:
        import anyio


logger = logging.getLogger(__name__)
# Note: these are atomic; the context is not a chainmap. If you have a nested
# load, and it's missing values from the config, it will never do a lookup into
# the parent context to look for an already-loaded value there.
# Note: technically the typing on this is incorrect, but it requires HKTs to be
# actually correct (as-written, this implies that the dict has all the same
# ``T``, and therefore effectively just one entry of ``{type[T]: T}``; really,
# we want to say, ``[K: type[V]]{K: V}``)
type _ConfigCtx[T: CfgInstanceIntersectable] = dict[type[T], T]
_CONFIG_CTX: ContextVar[_ConfigCtx] = ContextVar('_CONFIG_CTX', default={})  # noqa: B039


@dataclass(slots=True, frozen=True)
class _CfgFieldRouteKey:
    namespace: str | None
    fieldname: str


@dataclass(slots=True)
class _CfgFieldRoute:
    cfg_field_desc: CfgFieldDesc
    # Note: after filtering, and in the real search order (as determined by
    # the field source declaration, or the manager backend ordering)
    sources: list[_DefiniteCfgSource]


@dataclass(slots=True, frozen=True)
class _DefiniteCfgSource(CfgSource):
    backend: str


def _wip_keyspace_factory(
        ) -> dict[str | None, list[tuple[CfgFieldDesc, CfgSource]]]:
    return defaultdict(list)


@dataclass(slots=True, init=False)
class CfgManager:
    """The config manager is responsible for loading and refreshing
    configs.

    Typically, an application will have only a single config manager.
    If using multiple, you'll need to be careful to always pass explicit
    ``into_ctx`` objects to the loader methods, or to enter a new
    ``create_config_context()``. Failure to do so will result in the
    separate config managers reusing the same active config context,
    resulting in any overlapping ``cfg_classes`` being clobbered by the
    competing config managers.
    """
    cfg_classes: Annotated[
            Mapping[str | None, CfgMeta],
            Note('A read-only view of the config classes being managed.')]
    backends: Annotated[
            Mapping[str, CfgBackend],
            Note('A read-only view of the backends passed to the manager.')]
    type_coercer: Annotated[
            TypeCoercer | None,
            Note('''The type coercer to use for configs. Can be updated after
                creating the config manager. Set to ``None`` to remove.''')]
    _analysis: CfgAnalysis = field(repr=False, compare=False)
    _field_routes: dict[_CfgFieldRouteKey, _CfgFieldRoute] = field(
        repr=False, compare=False)
    _keyspaces_by_backend: dict[str, KeyspaceSummary] = field(
        repr=False, compare=False)

    def __init__(
            self,
            *cfg_classes: Annotated[
                CfgMeta,
                Note('The **concrete** config classes to manage.')],
            backends: Annotated[
                dict[str, CfgBackend],
                Note('''An ordered mapping of config backends to their names,
                    as referenced in config implementation classes.

                    Config backends are responsible for loading config fields.
                    Note that the ordering of the backends in the dictionary
                    determines the priority by which overlapping config
                    keyspaces are resolved: configs that appear earlier in the
                    dictionary will shadow those that appear later.

                    Ordering can be overwritten on a field-by-field basis by
                    explicitly specifying which backends to search, using
                    a ``CfgSource`` declaration.''')],
            type_coercer: TypeCoercer | None = None,):

        cfg_classes_ = {}
        self.cfg_classes = MappingProxyType(cfg_classes_)
        for concrete_cfg_cls in cfg_classes:
            norm_cfg_cls = normalize_config_cls(concrete_cfg_cls)
            cfg_cls_xable = cast(
                CfgClsIntersectable, norm_cfg_cls.concrete_cls)
            configatron_cfg = CfgInstanceIntersectable.get_configatron_cfg(
                cfg_cls_xable)
            namespace = configatron_cfg.namespace
            cfg_classes_[namespace] = concrete_cfg_cls

        # Copy and read-only-ify the backends; we want to make it clear that
        # this isn't allowed to change over time.
        self.backends = MappingProxyType({**backends})
        self.type_coercer = type_coercer

        self._analyze_configs()
        self._build_routes()

        missing_backends = set(self._keyspaces_by_backend) - set(self.backends)
        if missing_backends:
            raise ValueError(
                'Some backends required by config fields missing from '
                + 'config manager', missing_backends)

    def _analyze_configs(self):
        """Call this at the end of init to analyze the defined configs.
        This produces a config mapping, tracing all of the individual
        fields from their concrete classes back to their abstract ones
        to determine whether or not they're secret. It then eagerly
        calculates the lookup structures needed to actually load
        configs.
        """
        analysis: CfgAnalysis
        self._analysis = analysis = {}
        for namespace, concrete_cfg_cls in self.cfg_classes.items():
            norm_cfg_cls = normalize_config_cls(concrete_cfg_cls)

            if norm_cfg_cls.concrete_cls is not concrete_cfg_cls:
                raise ValueError(
                    'CfgManager must only be passed concrete config classes '
                    + 'to manage!', concrete_cfg_cls)

            analysis[namespace] = analyze_cfg_cls(namespace, norm_cfg_cls)

    # Bleh normalization is always really complicated, and that's pretty much
    # what we're doing here, hence the two noqa's
    def _build_routes(self):  # noqa: C901, PLR0912
        """Call this after analysis is done to construct a plan of how
        to load individual fields for the managed configs. Note that
        this applies filtering based on whether or not the backend
        supports secrets.
        """
        wip_keyspaces = defaultdict(_wip_keyspace_factory)
        backends = self.backends
        field_routes: dict[_CfgFieldRouteKey, _CfgFieldRoute]
        self._field_routes = field_routes = {}
        for namespace, field_analyses in self._analysis.items():
            for field_analysis in field_analyses:
                fieldname = field_analysis.field_desc.name
                sources: list[_DefiniteCfgSource] = []
                route_key = _CfgFieldRouteKey(namespace, fieldname)
                route = _CfgFieldRoute(
                    cfg_field_desc=field_analysis.field_desc,
                    sources=sources)
                field_routes[route_key] = route

                # Extract any CfgSource for the backend=None
                default_backend_src: CfgSource | None = None
                for source in field_analysis.sources:
                    if source.backend is None:
                        default_backend_src = source
                        break

                backend_ordering: dict[str, CfgSource]
                filtered_backends_unordered: set[str] = {
                    source.backend for source in field_analysis.sources
                    if source.backend is not None}

                # If all backends were explicit, we just need to grab their
                # ordering and associate it with the actual sources
                if default_backend_src is None:
                    backend_ordering = {
                        cast(str, source.backend): source
                        for source in field_analysis.sources}

                # If there was a backend=None, we need to add all of the other
                # backends
                else:
                    # If a config explicitly specifies some named backends AND
                    # a None, just tack on the remaining backends at the end
                    if len(field_analysis.sources) > 1:
                        backend_ordering = {
                            source.backend: source
                            for source in field_analysis.sources
                            if source.backend is not None}
                        backend_ordering.update({
                            backend_name: default_backend_src
                            for backend_name in backends
                            if backend_name not in filtered_backends_unordered
                        })

                    # Otherwise, default to the ordering defined when creating
                    # the config manager
                    else:
                        backend_ordering = dict.fromkeys(
                            backends, default_backend_src)

                    # Do this last so that we can retain the previous value
                    # for the ordering update (see above)
                    filtered_backends_unordered.update(self.backends)

                # Now we need to filter based on whether the field is secret
                # or plaintext, and whether or not the backend supports that
                # flavor
                if field_analysis.is_secret:
                    supported_backends = {
                        backend_name
                        for backend_name, backend in backends.items()
                        if backend.ALLOW_SECRET}
                else:
                    supported_backends = {
                        backend_name
                        for backend_name, backend in backends.items()
                        if backend.ALLOW_PLAINTEXT}

                prefilter_len = len(filtered_backends_unordered)
                # This bit actually does the filtering, so that we're only
                # checking at backends that support the correct configs
                filtered_backends_unordered &= supported_backends
                if prefilter_len > len(filtered_backends_unordered):
                    logger.info(
                        'Note: some config backends filtered for field w/ '
                        + 'namespace: %s, fieldname: %s, due to mismatched '
                        + 'flavor support (plaintext vs secret)',
                        namespace, fieldname)

                for backend_name, source in backend_ordering.items():
                    if backend_name in filtered_backends_unordered:
                        sources.append(_DefiniteCfgSource(
                            backend=backend_name,
                            lookup_keys=source.lookup_keys,
                            metadata=source.metadata))
                        # Note that we also want to sort things by backend, and
                        # we can piggyback on this for loop and do that here
                        # instead of requiring a separate method to do it
                        wip_keyspaces[backend_name][namespace].append(
                            (field_analysis.field_desc, source))

                if not sources:
                    logger.error(
                        'No config sources available for field w/ namespace: '
                        + '%s, fieldname %s. Config loading will fail!',
                        namespace, fieldname)

        # Finally, "distill" the keyspace into something immutable. We do this
        # because we want to protect against backends accidentally mutating
        # the full keyspace.
        keyspaces = self._keyspaces_by_backend = {}
        for backend, wip_by_namespace in wip_keyspaces.items():
            keyspaces[backend] = KeyspaceSummary(
                by_namespace=MappingProxyType({
                    namespace: tuple(field_tuples)
                    for namespace, field_tuples in wip_by_namespace.items()}))

    def audit_configs(self) -> CfgAnalysis:
        """This generates a summary of all concrete config fields passed
        to the config manager during its creation, grouped by the
        namespace of their parent concrete config.
        """
        return self._analysis

    # This isn't implemented yet, so exclude it from the docs
    @docnote(DocnoteConfig(include_in_docs=False))
    @contextmanager
    def poll_sync(self, refresh_after_max: float):
        """The sync version of the config manager runs as a background
        thread, refreshing the config as per the ``refresh_after_max``
        setting.
        """
        raise NotImplementedError
        yield
        """How it will work:
        ++  you'll need to calculate a min refresh rate lookup during the
            __init__
        ++  you'll need to also keep track of all deadlines for refreshes
        ++  then do a ``load_once``, and update all the deadlines based on
            the refresh rate
        ++  then sleep until the first deadline
        ++  then reload that particular field (or batch of fields)
        ++  then do a ``dc_replace`` on all affected configs, so that you
            only update the values that have changed
        ++  then set that as the new value within the config context
        ++  then repeat infinitely for each of the deadlines
        """

    # This isn't implemented yet, so exclude it from the docs
    @docnote(DocnoteConfig(include_in_docs=False))
    @asynccontextmanager
    async def poll_async(self, refresh_after_max: float):
        """The async version of the config manager runs as a background
        task using anyio, refreshing the config as per the
        ``refresh_after_max`` setting.
        """
        raise NotImplementedError
        yield

    def load_once_sync(self, *, into_ctx: _ConfigCtx | None = None):
        """This performs a single static load of all managed config
        classes. By default, the currently active config context will
        be updated with the loaded values; if desired, a dictionary
        can be passed by the ``into_ctx`` argument, and the values
        will instead be inserted into it.

        The sync loader performs all work within the current thread.
        """
        results_by_backend: dict[str, dict[CfgFieldDesc, Any]] = {}
        for backend_name, keyspace in self._keyspaces_by_backend.items():
            backend = self.backends[backend_name]
            results_by_backend[backend_name] = backend.load_sync(
                keyspace, keyspace)

        ctx = self._distill_load_results(results_by_backend)

        if into_ctx is None:
            active_ctx = _CONFIG_CTX.get()
            active_ctx.update(ctx)
        else:
            into_ctx.update(ctx)

    async def load_once_async(self, *, into_ctx: _ConfigCtx | None = None):
        """This performs a single static load of all managed config
        classes. By default, the currently active config context will
        be updated with the loaded values; if desired, a dictionary
        can be passed by the ``into_ctx`` argument, and the values
        will instead be inserted into it.

        The sync loader performs all work within the current async task.
        """
        results_by_backend: dict[str, dict[CfgFieldDesc, Any]] = {}
        async with anyio.create_task_group() as task_group:
            for backend_name, keyspace in self._keyspaces_by_backend.items():
                task_group.start_soon(
                    _wrap_load_async,
                    results_by_backend,
                    backend_name,
                    self.backends[backend_name],
                    keyspace,
                    keyspace)

        ctx = self._distill_load_results(results_by_backend)

        if into_ctx is None:
            active_ctx = _CONFIG_CTX.get()
            active_ctx.update(ctx)
        else:
            into_ctx.update(ctx)

    def _distill_load_results(
            self,
            results_by_backend: dict[str, dict[CfgFieldDesc, Any]]
            ) -> _ConfigCtx:
        """This is responsible for creating a config context from the
        backend results. **Note that this only works for the initial
        load call!** Polling requires more sophisticated logic, because
        it needs to maintain expirations, replace individual fields
        while keeping the rest of a config class intact, etc.
        """
        retval: _ConfigCtx = {}
        for namespace, field_analyses in self._analysis.items():
            cfg_cls = self.cfg_classes[namespace]

            kwargs: dict[str, Any] = {}
            for field_analysis in field_analyses:
                fieldname = field_analysis.field_desc.name
                field_route = self._field_routes[_CfgFieldRouteKey(
                    namespace, fieldname)]

                for source in field_route.sources:
                    value = results_by_backend[source.backend].get(
                        field_analysis.field_desc, _MISSING)
                    if value is not _MISSING:
                        kwargs[fieldname] = value
                        break

                # No value loaded. Log (so that it's clearer what happened),
                # but allow the constructor to raise
                else:
                    logger.error(
                        'Missing config value during loading. Namespace %s, '
                        + 'fieldname %s. Load will fail.',
                        namespace, fieldname)

            if self.type_coercer is None:
                retval[cfg_cls] = cfg_cls(**kwargs)
            else:
                retval[cfg_cls] = self.type_coercer(cfg_cls, kwargs)

        return retval

    def __setattr__(self, name: str, value: Any):
        """Allow the type_coercer to change over time, and allow
        all fields to be set if they don't yet exist. For everything
        else, there's AttributeError.
        """
        protected_attrs = {dc_field.name for dc_field in fields(self)}
        protected_attrs.discard('type_coercer')
        if name in protected_attrs and hasattr(self, name):
            raise AttributeError(f'``CfgManager.{name}`` cannot be updated.')

        super(CfgManager, self).__setattr__(name, value)

    def __delattr__(self, name: str):
        """Forbid deleting any of our fields.
        """
        protected_attrs = {dc_field.name for dc_field in fields(self)}
        if name in protected_attrs:
            raise AttributeError(f'``CfgManager.{name}`` cannot be deleted.')

        super(CfgManager, self).__delattr__(name)


@contextmanager
def create_config_context() -> Generator[_ConfigCtx, None, None]:
    """Creates and activates a new config context. Primarily intended
    for use in testing, but might be useful in other sitations as well.

    Under the hood, this uses a ``ContextVar`` to override the active
    config context. This means that all contextually-nested calls to
    load or retrieve config values will operate on the config context
    created by this context manager.
    """
    ctx: _ConfigCtx = {}
    ctx_token = _CONFIG_CTX.set(ctx)
    try:
        yield ctx
    finally:
        _CONFIG_CTX.reset(ctx_token)


async def _wrap_load_async(
        results_by_backend: dict[str, dict[CfgFieldDesc, Any]],
        backend_name: str,
        backend: CfgBackend,
        request: KeyspaceSummary,
        full_keyspace: KeyspaceSummary):
    """Wraps loading such that results can be retrieved.
    """
    results_by_backend[backend_name] = await backend.load_async(
        request, full_keyspace)


class _Missing(Enum):
    MISSING = 'missing'
_MISSING = _Missing.MISSING


def get_active_cfg[T](cfg_cls: type[T]) -> T:
    """Given a config class, constructs or loads the most-correct
    currently-active version of that config class and returns it.

    TODO: this needs to also check to see if the config class is a
    concrete or abstract one! Both are supported, but the lookup is
    always defined w.r.t. the abstract config.
    """
    normalized_cfg_cls = normalize_config_cls(cast(CfgMeta, cfg_cls))
    cfg_ctx = _CONFIG_CTX.get()

    concrete_cfg = cfg_ctx.get(normalized_cfg_cls.concrete_cls, None)
    if concrete_cfg is None:
        raise ConfigNotLoaded(
            'No concrete config implementation found for the passed '
            + '``cfg_cls`` found in the currently active config context!',
            cfg_cls, normalized_cfg_cls.concrete_cls)

    return concrete_cfg
