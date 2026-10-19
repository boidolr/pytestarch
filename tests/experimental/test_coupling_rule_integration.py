from __future__ import annotations

import re

import pytest

from pytestarch import EvaluableArchitecture
from pytestarch.experimental import CouplingRule


def test_coupling_rule_on_fixture_project(
    flat_project_1: EvaluableArchitecture,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named("flat_test_project_1.exporter")
        .should_have_max_efferent_coupling(3)
        .should_have_max_afferent_coupling(1)
    )

    rule.assert_applies(flat_project_1)


def test_coupling_rule_reports_fixture_project_violation(
    flat_project_1: EvaluableArchitecture,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named("flat_test_project_1.exporter")
        .should_have_max_efferent_coupling(2)
    )

    with pytest.raises(
        AssertionError,
        match=re.escape(
            '"flat_test_project_1.exporter" has an efferent coupling of 3, '
            "but the maximum is 2."
        ),
    ):
        rule.assert_applies(flat_project_1)
