"""Draft of a coupling rule, inspired by the afferent and efferent coupling
metrics for software modules.

The rule is experimental: its API is not finalized yet and may change or be
removed without notice. It lives in :mod:`pytestarch.experimental` together with
the other draft architecture rules.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from pytestarch.eval_structure.evaluable_architecture import (
    EvaluableArchitecture,
    Module,
    ModuleFilter,
    ModuleNameFilter,
    ModuleNameRegexFilter,
    ParentModuleNameFilter,
)
from pytestarch.eval_structure.module_name_converter import ModuleNameConverter
from pytestarch.query_language.base_language import ModuleSpecification, RuleApplier
from pytestarch.query_language.exceptions import ImproperlyConfigured
from pytestarch.utils.decorators import deprecated
from pytestarch.utils.partial_match_to_regex_converter import (
    convert_partial_match_to_regex,
)

CouplingMetric = Literal["efferent", "afferent"]


@dataclass(frozen=True)
class CouplingRequirement:
    """Maximum allowed coupling per module for the checks in this rule."""

    modules: Sequence[ModuleFilter]
    max_efferent: int | None
    max_afferent: int | None


@dataclass(frozen=True)
class CouplingViolation:
    """A module whose coupling exceeds the configured maximum."""

    module: Module
    metric: CouplingMetric
    actual: int
    maximum: int
    coupled_modules: tuple[Module, ...]


@dataclass
class CouplingRuleConfiguration:
    modules_to_check: Sequence[ModuleFilter] | None = None
    max_efferent: int | None = None
    max_afferent: int | None = None


class CouplingRule(RuleApplier, ModuleSpecification[RuleApplier]):
    r"""Represents a coupling rule of the form
    modules \[such as 'are named X'\] should have at most \[N\] \[efferent/afferent\] coupling.

    Example:
        CouplingRule() \
            .modules_that() \
            .are_named("my_project.services") \
            .should_have_max_efferent_coupling(5) \
            .should_have_max_afferent_coupling(10) \
            .assert_applies(evaluable)
    """

    def __init__(self) -> None:
        self._configuration = CouplingRuleConfiguration()
        self._modules_to_check_to_be_specified_next = False

    def modules_that(self) -> CouplingRule:
        self._modules_to_check_to_be_specified_next = True
        return self

    def are_sub_modules_of(self, modules: str | Sequence[str]) -> CouplingRule:
        self._set_modules(
            modules, lambda name: ParentModuleNameFilter(parent_module=name)
        )
        return self

    def are_named(self, names: str | Sequence[str]) -> CouplingRule:
        self._assert_no_wildcards(names)
        self._set_modules(names, lambda name: ModuleNameFilter(name=name))
        return self

    @deprecated
    def have_name_containing(self, partial_name: str | Sequence[str]) -> CouplingRule:
        self._set_modules(
            partial_name,
            lambda name: ModuleNameRegexFilter(
                name=convert_partial_match_to_regex(name)
            ),
        )
        return self

    def have_name_matching(self, regex: str) -> CouplingRule:
        self._set_modules(regex, lambda name: ModuleNameRegexFilter(name=name))
        return self

    def should_have_max_efferent_coupling(self, max_coupling: int) -> CouplingRule:
        """Limits the number of distinct modules the selected modules may import."""
        self._configuration.max_efferent = self._validate_max_coupling(max_coupling)
        return self

    def should_have_max_afferent_coupling(self, max_coupling: int) -> CouplingRule:
        """Limits the number of distinct modules that may import the selected modules."""
        self._configuration.max_afferent = self._validate_max_coupling(max_coupling)
        return self

    def assert_applies(self, evaluable: EvaluableArchitecture) -> None:
        """Checks the configured coupling thresholds against the evaluable.

        Args:
            evaluable: module dependency structure to compare the rule against.

        Raises:
            AssertionError: if at least one threshold is exceeded.
            ImproperlyConfigured: if modules or thresholds are missing.
            ImpossibleMatch: if a regex filter matches no module.
        """
        self._assert_required_configuration_present()
        modules, _ = ModuleNameConverter.convert(
            self._modules_to_check_or_error, evaluable
        )
        requirement = CouplingRequirement(
            modules=modules,
            max_efferent=self._configuration.max_efferent,
            max_afferent=self._configuration.max_afferent,
        )

        violations = _get_coupling_violations(evaluable, requirement)
        if violations:
            raise AssertionError(
                CouplingViolationMessageGenerator().create_message(violations)
            )

    def __str__(self) -> str:
        self._assert_required_configuration_present()
        modules_to_check = self._modules_to_check_or_error

        subject_prefix = (
            "Sub modules of " if modules_to_check[0].identifier_is_parent_module else ""
        )
        names = ", ".join(sorted(module.identifier for module in modules_to_check))

        thresholds = []
        if self._configuration.max_efferent is not None:
            thresholds.append(
                f"at most {self._configuration.max_efferent} efferent coupling"
            )
        if self._configuration.max_afferent is not None:
            thresholds.append(
                f"at most {self._configuration.max_afferent} afferent coupling"
            )

        return (
            f'Coupling rule: {subject_prefix}"{names}" '
            f"should have {' and '.join(thresholds)}."
        )

    @property
    def _modules_to_check_or_error(self) -> Sequence[ModuleFilter]:
        modules_to_check = self._configuration.modules_to_check
        if not modules_to_check:
            raise ImproperlyConfigured(
                "Specify the modules to check via modules_that() first."
            )
        return modules_to_check

    def _set_modules(
        self,
        module_names: str | Sequence[str],
        create_module_fn: Callable[[str], ModuleFilter],
    ) -> None:
        if not self._modules_to_check_to_be_specified_next:
            raise ImproperlyConfigured(
                "Specify the modules to check via modules_that() first."
            )

        names = [module_names] if isinstance(module_names, str) else module_names
        self._configuration.modules_to_check = [
            create_module_fn(name) for name in names
        ]

    def _assert_required_configuration_present(self) -> None:
        modules_missing = not self._configuration.modules_to_check
        thresholds_missing = (
            self._configuration.max_efferent is None
            and self._configuration.max_afferent is None
        )

        messages = []
        if modules_missing:
            messages.append("the modules to check via modules_that()")
        if thresholds_missing:
            messages.append(
                "at least one maximum coupling via "
                "should_have_max_efferent_coupling() or "
                "should_have_max_afferent_coupling()"
            )

        if messages:
            raise ImproperlyConfigured(f"Specify {', and '.join(messages)}.")

    @staticmethod
    def _assert_no_wildcards(names: str | Sequence[str]) -> None:
        if isinstance(names, str):
            names = [names]

        for name in names:
            if "*" in name:
                raise ImproperlyConfigured(
                    f'Wildcard "*" detected in module name "{name}". '
                    'Use "have_name_matching" with a regex pattern instead.'
                )

    @staticmethod
    def _validate_max_coupling(max_coupling: int) -> int:
        if isinstance(max_coupling, bool) or not isinstance(max_coupling, int):
            raise ImproperlyConfigured("Maximum coupling must be an integer.")
        if max_coupling < 0:
            raise ImproperlyConfigured(
                "Maximum coupling must be greater than or equal to zero."
            )
        return max_coupling


def _get_coupling_violations(
    evaluable: EvaluableArchitecture,
    requirement: CouplingRequirement,
) -> list[CouplingViolation]:
    """Returns all coupling thresholds exceeded by the evaluable.

    Expects concrete module filters and validated, non-negative thresholds. The
    public entry point is :class:`CouplingRule`.
    """
    couplings = evaluable.get_coupling(requirement.modules)
    violations = []

    for module, coupling in couplings.items():
        if (
            requirement.max_efferent is not None
            and coupling.efferent_coupling > requirement.max_efferent
        ):
            violations.append(
                CouplingViolation(
                    module=module,
                    metric="efferent",
                    actual=coupling.efferent_coupling,
                    maximum=requirement.max_efferent,
                    coupled_modules=tuple(
                        sorted(
                            coupling.efferent_modules,
                            key=lambda coupled: coupled.identifier,
                        )
                    ),
                )
            )

        if (
            requirement.max_afferent is not None
            and coupling.afferent_coupling > requirement.max_afferent
        ):
            violations.append(
                CouplingViolation(
                    module=module,
                    metric="afferent",
                    actual=coupling.afferent_coupling,
                    maximum=requirement.max_afferent,
                    coupled_modules=tuple(
                        sorted(
                            coupling.afferent_modules,
                            key=lambda coupled: coupled.identifier,
                        )
                    ),
                )
            )

    violations.sort(
        key=lambda violation: (violation.module.identifier, violation.metric)
    )
    return violations


class CouplingViolationMessageGenerator:
    """Formats coupling violations as human-readable assertion messages."""

    def create_message(self, violations: Sequence[CouplingViolation]) -> str:
        """Returns one line per coupling violation."""
        return "\n".join(self._create_message(violation) for violation in violations)

    @staticmethod
    def _create_message(violation: CouplingViolation) -> str:
        if violation.module.is_single_module:
            subject = f'"{violation.module.identifier}"'
            verb = "has"
        else:
            subject = f'Sub modules of "{violation.module.identifier}"'
            verb = "have"

        coupled_modules = ", ".join(
            f'"{module.identifier}"' for module in violation.coupled_modules
        )
        return (
            f"{subject} {verb} an {violation.metric} coupling of "
            f"{violation.actual}, but the maximum is {violation.maximum}. "
            f"Coupled modules: {coupled_modules}."
        )
