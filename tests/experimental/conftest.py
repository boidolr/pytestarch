from __future__ import annotations

import pytest
from eval_structure.evaluable_graph.conftest import (
    MODULE_A,
    MODULE_B,
    MODULE_C,
    MODULE_D,
    MODULE_E,
    MODULE_F,
)

from pytestarch.eval_structure.evaluable_graph import EvaluableArchitectureGraph
from pytestarch.eval_structure.networkxgraph import NetworkxGraph
from pytestarch.eval_structure_generation.file_import.import_types import AbsoluteImport


@pytest.fixture
def submodule_evaluable() -> EvaluableArchitectureGraph:
    all_modules = [MODULE_A, MODULE_B, MODULE_C, MODULE_D, MODULE_E, MODULE_F]
    imports = [
        AbsoluteImport(MODULE_F, MODULE_C),
        AbsoluteImport(MODULE_C, MODULE_A),
        AbsoluteImport(MODULE_C, MODULE_B),
    ]
    return EvaluableArchitectureGraph(NetworkxGraph(all_modules, imports))
