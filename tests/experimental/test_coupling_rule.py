from __future__ import annotations

import re

import pytest
from eval_structure.evaluable_graph.conftest import (
    MODULE_A,
    MODULE_C,
    MODULE_E,
)

from pytestarch.eval_structure.evaluable_graph import EvaluableArchitectureGraph
from pytestarch.eval_structure.exceptions import ImpossibleMatch
from pytestarch.experimental import CouplingRule
from pytestarch.query_language.exceptions import ImproperlyConfigured
from pytestarch.query_language.multiple_rule_applier import MultipleRuleApplier


def test_coupling_rule_applies_at_threshold(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_E)
        .should_have_max_efferent_coupling(1)
        .should_have_max_afferent_coupling(1)
    )

    rule.assert_applies(submodule_evaluable)


def test_coupling_rule_fails_above_efferent_threshold(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_E)
        .should_have_max_efferent_coupling(0)
    )

    with pytest.raises(
        AssertionError,
        match=re.escape(
            '"E" has an efferent coupling of 1, but the maximum is 0. '
            'Coupled modules: "C".'
        ),
    ):
        rule.assert_applies(submodule_evaluable)


def test_coupling_rule_reports_both_threshold_violations(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_C)
        .should_have_max_efferent_coupling(1)
        .should_have_max_afferent_coupling(0)
    )

    with pytest.raises(AssertionError) as error:
        rule.assert_applies(submodule_evaluable)

    message = str(error.value)
    assert '"C" has an afferent coupling of 1, but the maximum is 0.' in message
    assert '"C" has an efferent coupling of 2, but the maximum is 1.' in message
    assert message.index("afferent") < message.index("efferent")


def test_coupling_rule_message_for_submodule_group(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_sub_modules_of(MODULE_A)
        .should_have_max_afferent_coupling(0)
    )

    with pytest.raises(AssertionError) as error:
        rule.assert_applies(submodule_evaluable)

    assert (
        'Sub modules of "E.A" have an afferent coupling of 1, but the maximum is 0.'
        in str(error.value)
    )


def test_coupling_rule_checks_each_subject(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named([MODULE_E, MODULE_C])
        .should_have_max_efferent_coupling(1)
    )

    with pytest.raises(AssertionError) as error:
        rule.assert_applies(submodule_evaluable)

    message = str(error.value)
    assert '"E"' not in message
    assert '"C" has an efferent coupling of 2' in message


def test_coupling_rule_supports_regex_subjects(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    passing = (
        CouplingRule()
        .modules_that()
        .have_name_matching(r"E\.A$")
        .should_have_max_afferent_coupling(1)
    )
    passing.assert_applies(submodule_evaluable)

    failing = (
        CouplingRule()
        .modules_that()
        .have_name_matching(r"E\.A$")
        .should_have_max_afferent_coupling(0)
    )
    with pytest.raises(
        AssertionError, match=re.escape('"E.A" has an afferent coupling of 1')
    ):
        failing.assert_applies(submodule_evaluable)


def test_coupling_rule_regex_without_match_raises(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .have_name_matching("does-not-match")
        .should_have_max_efferent_coupling(0)
    )

    with pytest.raises(ImpossibleMatch):
        rule.assert_applies(submodule_evaluable)


def test_coupling_rule_requires_modules(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = CouplingRule().should_have_max_efferent_coupling(1)

    with pytest.raises(ImproperlyConfigured, match="modules to check"):
        rule.assert_applies(submodule_evaluable)


def test_coupling_rule_requires_at_least_one_threshold(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = CouplingRule().modules_that().are_named(MODULE_E)

    with pytest.raises(ImproperlyConfigured, match="maximum coupling"):
        rule.assert_applies(submodule_evaluable)


def test_coupling_rule_rejects_negative_threshold() -> None:
    with pytest.raises(ImproperlyConfigured, match="greater than or equal to zero"):
        CouplingRule().should_have_max_efferent_coupling(-1)


def test_coupling_rule_rejects_bool_threshold() -> None:
    with pytest.raises(ImproperlyConfigured, match="integer"):
        CouplingRule().should_have_max_efferent_coupling(True)


def test_coupling_rule_accepts_zero_threshold(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_A)
        .should_have_max_efferent_coupling(0)
    )

    rule.assert_applies(submodule_evaluable)


def test_coupling_rule_rejects_wildcards() -> None:
    with pytest.raises(ImproperlyConfigured, match="Wildcard"):
        CouplingRule().modules_that().are_named("E*")


def test_coupling_rule_requires_modules_that_first() -> None:
    with pytest.raises(ImproperlyConfigured, match="modules_that"):
        CouplingRule().are_named(MODULE_E)


def test_coupling_rule_deprecated_name_containing() -> None:
    with pytest.warns(DeprecationWarning):
        CouplingRule().modules_that().have_name_containing("E.A")


def test_coupling_rule_str_for_named_and_group_subjects() -> None:
    named = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_E)
        .should_have_max_efferent_coupling(1)
        .should_have_max_afferent_coupling(2)
    )
    assert str(named) == (
        'Coupling rule: "E" should have at most 1 efferent coupling '
        "and at most 2 afferent coupling."
    )

    grouped = (
        CouplingRule()
        .modules_that()
        .are_sub_modules_of(MODULE_A)
        .should_have_max_efferent_coupling(0)
    )
    assert str(grouped) == (
        'Coupling rule: Sub modules of "E.A" should have at most 0 efferent coupling.'
    )


def test_coupling_rule_can_be_reused(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    rule = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_E)
        .should_have_max_efferent_coupling(1)
    )

    rule.assert_applies(submodule_evaluable)
    rule.assert_applies(submodule_evaluable)


def test_coupling_rule_composes_with_multiple_rule_applier(
    submodule_evaluable: EvaluableArchitectureGraph,
) -> None:
    passing = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_E)
        .should_have_max_efferent_coupling(1)
    )
    failing = (
        CouplingRule()
        .modules_that()
        .are_named(MODULE_E)
        .should_have_max_efferent_coupling(0)
    )

    with pytest.raises(AssertionError, match="efferent coupling"):
        MultipleRuleApplier([passing, failing]).assert_applies(submodule_evaluable)
