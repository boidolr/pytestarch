"""Calculates efferent and afferent coupling from an abstract dependency graph."""

from __future__ import annotations

from collections.abc import Iterable

from pytestarch.eval_structure.breadth_first_searches import get_all_submodules_of
from pytestarch.eval_structure.evaluable_architecture import (
    Coupling,
    CouplingByBaseModule,
    ModuleFilter,
)
from pytestarch.eval_structure.evaluable_structures import AbstractGraph
from pytestarch.eval_structure.types import get_parent_modules
from pytestarch.eval_structure.utils import filter_to_module, to_module


def get_coupling(
    graph: AbstractGraph, modules: Iterable[ModuleFilter]
) -> CouplingByBaseModule:
    """Returns efferent and afferent coupling per requested module group.

    For a named module, the group consists of the module itself and its
    submodules. For a parent-module filter, the group consists of the strict
    submodules of the parent; the parent itself is internal and not part of the
    group. Parent modules and other ancestors are treated as internal as well,
    so only dependencies that leave the module's hierarchy are counted.
    Parent/child hierarchy edges are not dependencies. Coupling counts distinct
    modules, not import statements, and does not include transitive
    dependencies.

    Args:
        graph: dependency graph to inspect.
        modules: concrete module filters. Regex filters must be resolved by the
            caller before calling this function.

    Returns:
        Coupling per requested module, keyed by the module or module group.

    Raises:
        ValueError: if a regex filter is passed instead of a concrete module.
        ModuleUnknown: if a requested module is not present in the graph.
    """
    result: CouplingByBaseModule = {}

    for module_filter in set(modules):
        if module_filter.identifier_is_regex:
            raise ValueError(
                "get_coupling expects concrete module filters; "
                "resolve regex filters first."
            )

        scope = get_all_submodules_of(graph, module_filter)

        if module_filter.identifier_is_parent_module:
            scope.discard(module_filter.identifier)

        excluded = scope | set(get_parent_modules(module_filter.identifier))

        if module_filter.identifier_is_parent_module:
            excluded.add(module_filter.identifier)

        efferent_modules = set()
        afferent_modules = set()

        for node in scope:
            for successor in graph.direct_successor_nodes(node):
                if graph.parent_child_relationship(node, successor):
                    continue
                if successor not in excluded:
                    efferent_modules.add(to_module(successor))

            for predecessor in graph.direct_predecessor_nodes(node):
                if graph.parent_child_relationship(predecessor, node):
                    continue
                if predecessor not in excluded:
                    afferent_modules.add(to_module(predecessor))

        result[filter_to_module(module_filter)] = Coupling(
            efferent_modules=frozenset(efferent_modules),
            afferent_modules=frozenset(afferent_modules),
        )

    return result
