from __future__ import annotations

import pytest

from eval_structure.evaluable_graph.conftest import (
    MODULE_A,
    MODULE_C,
    MODULE_E,
)
from pytestarch.eval_structure.evaluable_architecture import (
    Module,
    ModuleGroup,
    ModuleNameFilter,
    ModuleNameRegexFilter,
    ParentModuleNameFilter,
)
from pytestarch.eval_structure.evaluable_graph import EvaluableArchitectureGraph
from pytestarch.eval_structure.exceptions import ModuleUnknown
from pytestarch.eval_structure.networkxgraph import NetworkxGraph
from pytestarch.eval_structure_generation.file_import.import_types import AbsoluteImport


def test_named_module_coupling(submodule_evaluable: EvaluableArchitectureGraph) -> None:
    coupling = submodule_evaluable.get_coupling([ModuleNameFilter(name=MODULE_E)])[
        Module(identifier=MODULE_E)
    ]

    assert coupling.efferent_coupling == 1
    assert coupling.afferent_coupling == 1
    assert coupling.efferent_modules == frozenset({Module(identifier=MODULE_C)})
    assert coupling.afferent_modules == frozenset({Module(identifier=MODULE_C)})


def test_named_submodule_coupling(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    coupling = submodule_evaluable.get_coupling([ModuleNameFilter(name=MODULE_A)])[
        Module(identifier=MODULE_A)
    ]

    assert coupling.efferent_coupling == 0
    assert coupling.afferent_coupling == 1
    assert coupling.afferent_modules == frozenset({Module(identifier=MODULE_C)})


def test_parent_module_filter_coupling(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    coupling = submodule_evaluable.get_coupling(
        [ParentModuleNameFilter(parent_module=MODULE_A)]
    )[ModuleGroup(identifier=MODULE_A)]

    assert coupling.efferent_coupling == 0
    assert coupling.afferent_coupling == 1
    assert coupling.afferent_modules == frozenset({Module(identifier=MODULE_C)})


def test_coupling_counts_distinct_modules_not_edges() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "A.x", "B"],
            [AbsoluteImport("A", "B"), AbsoluteImport("A.x", "B")],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="A")])[Module(identifier="A")]

    assert coupling.efferent_coupling == 1
    assert coupling.efferent_modules == frozenset({Module(identifier="B")})


def test_imports_between_submodules_are_internal() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "A.x", "A.y"],
            [AbsoluteImport("A.x", "A.y"), AbsoluteImport("A.y", "A.x")],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="A")])[Module(identifier="A")]

    assert coupling.efferent_coupling == 0
    assert coupling.afferent_coupling == 0


def test_parent_child_import_is_not_counted() -> None:
    # A -> A.x is a real import, but the graph stores it as a hierarchy edge.
    # The family boundary must ignore it for both the parent and the child.
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "A.x", "B", "C"],
            [
                AbsoluteImport("A", "A.x"),
                AbsoluteImport("A.x", "B"),
                AbsoluteImport("C", "A.x"),
            ],
        )
    )

    couplings = graph.get_coupling(
        [ModuleNameFilter(name="A"), ModuleNameFilter(name="A.x")]
    )

    parent = couplings[Module(identifier="A")]
    assert parent.efferent_modules == frozenset({Module(identifier="B")})
    assert parent.afferent_modules == frozenset({Module(identifier="C")})

    child = couplings[Module(identifier="A.x")]
    assert child.efferent_modules == frozenset({Module(identifier="B")})
    assert child.afferent_modules == frozenset({Module(identifier="C")})


def test_sibling_coupling_counts_for_child_but_not_for_parent() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["X", "X.A", "X.B"],
            [AbsoluteImport("X.B", "X.A")],
        )
    )

    couplings = graph.get_coupling(
        [ModuleNameFilter(name="X"), ModuleNameFilter(name="X.A")]
    )

    parent = couplings[Module(identifier="X")]
    assert parent.efferent_coupling == 0
    assert parent.afferent_coupling == 0

    child = couplings[Module(identifier="X.A")]
    assert child.efferent_coupling == 0
    assert child.afferent_coupling == 1
    assert child.afferent_modules == frozenset({Module(identifier="X.B")})


def test_coupling_of_module_without_dependencies() -> None:
    graph = EvaluableArchitectureGraph(NetworkxGraph(["A", "B"], []))

    coupling = graph.get_coupling([ModuleNameFilter(name="A")])[Module(identifier="A")]

    assert coupling.efferent_coupling == 0
    assert coupling.afferent_coupling == 0


def test_level_limit_is_respected() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["src.A", "src.A.x", "src.B"],
            [AbsoluteImport("src.A.x", "src.B")],
            level_limit=1,
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="src.A")])[
        Module(identifier="src.A")
    ]

    assert coupling.efferent_coupling == 1
    assert coupling.efferent_modules == frozenset({Module(identifier="src.B")})


def test_regex_filter_is_rejected(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    with pytest.raises(ValueError, match="concrete module filters"):
        submodule_evaluable.get_coupling([ModuleNameRegexFilter(name=".*")])


def test_absent_module_raises(submodule_evaluable: EvaluableArchitectureGraph) -> None:
    with pytest.raises(ModuleUnknown):
        submodule_evaluable.get_coupling([ModuleNameFilter(name="Missing")])


def test_distinct_targets_in_same_package_are_counted() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "B.x", "B.y"],
            [AbsoluteImport("A", "B.x"), AbsoluteImport("A", "B.y")],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="A")])[Module(identifier="A")]

    assert coupling.efferent_coupling == 2
    assert coupling.efferent_modules == frozenset(
        {Module(identifier="B.x"), Module(identifier="B.y")}
    )


def test_parent_filter_excludes_parents_own_imports() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "A.x", "B", "C"],
            [
                AbsoluteImport("A", "C"),
                AbsoluteImport("A.x", "B"),
                AbsoluteImport("C", "A"),
                AbsoluteImport("B", "A.x"),
            ],
        )
    )

    coupling = graph.get_coupling([ParentModuleNameFilter(parent_module="A")])[
        ModuleGroup(identifier="A")
    ]

    assert coupling.efferent_modules == frozenset({Module(identifier="B")})
    assert coupling.afferent_modules == frozenset({Module(identifier="B")})


def test_parent_filter_ignores_imports_between_submodules() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["X", "X.a", "X.b"],
            [AbsoluteImport("X.a", "X.b")],
        )
    )

    coupling = graph.get_coupling([ParentModuleNameFilter(parent_module="X")])[
        ModuleGroup(identifier="X")
    ]

    assert coupling.efferent_coupling == 0
    assert coupling.afferent_coupling == 0


def test_imports_to_ancestors_are_excluded() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "A.x", "B"],
            [
                AbsoluteImport("A.x", "A"),
                AbsoluteImport("A.x", "B"),
            ],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="A.x")])[
        Module(identifier="A.x")
    ]

    assert coupling.efferent_modules == frozenset({Module(identifier="B")})
    assert coupling.afferent_coupling == 0


def test_imports_to_grandparents_are_excluded() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "A.x", "A.x.y", "B"],
            [
                AbsoluteImport("A", "A.x.y"),
                AbsoluteImport("A.x.y", "B"),
            ],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="A.x.y")])[
        Module(identifier="A.x.y")
    ]

    assert coupling.efferent_modules == frozenset({Module(identifier="B")})
    assert coupling.afferent_coupling == 0


def test_external_modules_are_counted() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "ext", "ext.sub", "ext.other"],
            [
                AbsoluteImport("A", "ext.sub"),
                AbsoluteImport("A", "ext.other"),
            ],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="A")])[Module(identifier="A")]

    assert coupling.efferent_coupling == 2
    assert coupling.efferent_modules == frozenset(
        {Module(identifier="ext.sub"), Module(identifier="ext.other")}
    )


def test_overlapping_subjects_are_checked_independently() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["X", "X.A", "Importer"],
            [AbsoluteImport("Importer", "X.A")],
        )
    )

    couplings = graph.get_coupling(
        [ModuleNameFilter(name="X"), ModuleNameFilter(name="X.A")]
    )

    assert couplings[Module(identifier="X")].afferent_modules == frozenset(
        {Module(identifier="Importer")}
    )
    assert couplings[Module(identifier="X.A")].afferent_modules == frozenset(
        {Module(identifier="Importer")}
    )


def test_ancestor_detection_is_boundary_safe() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["app", "application", "app.x"],
            [AbsoluteImport("app", "application")],
        )
    )

    coupling = graph.get_coupling([ModuleNameFilter(name="app")])[
        Module(identifier="app")
    ]

    assert coupling.efferent_modules == frozenset({Module(identifier="application")})


def test_duplicate_filters_are_deduplicated() -> None:
    graph = EvaluableArchitectureGraph(
        NetworkxGraph(
            ["A", "B"],
            [AbsoluteImport("A", "B")],
        )
    )

    couplings = graph.get_coupling(
        [ModuleNameFilter(name="A"), ModuleNameFilter(name="A")]
    )

    assert len(couplings) == 1
    assert couplings[Module(identifier="A")].efferent_coupling == 1
