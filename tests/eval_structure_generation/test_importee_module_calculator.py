from __future__ import annotations

from pathlib import Path

from pytestarch.eval_structure_generation.file_import.import_types import AbsoluteImport
from pytestarch.eval_structure_generation.file_import.importee_module_calculator import (
    ImporteeModuleCalculator,
)

ROOT_PATH = Path("/dummy/project/src")  # root module name: "src"
ROOT_MODULE_NAME = "src"


def calculate(imports, all_modules):
    return set(
        ImporteeModuleCalculator(
            ROOT_PATH, ROOT_MODULE_NAME
        ).calculate_importee_modules(imports, all_modules)
    )


def test_external_importee_and_its_parents_are_added() -> None:
    result = calculate(
        [AbsoluteImport("src.moduleA.fileA", "os.path")],
        ["src.moduleA.fileA"],
    )

    assert result == {"src.moduleA.fileA", "os.path", "os"}


def test_internal_importee_is_not_added_as_external_module() -> None:
    """Importees belonging to the scanned root module must not be treated as
    external dependencies (regression test for
    https://github.com/zyskarch/pytestarch/issues/144)."""
    result = calculate(
        [AbsoluteImport("src.moduleA.fileA", "src.moduleB.fileB")],
        ["src.moduleA.fileA"],
    )

    assert result == {"src.moduleA.fileA"}


def test_importee_equal_to_root_module_name_is_not_added() -> None:
    result = calculate(
        [AbsoluteImport("src.moduleA.fileA", "src")],
        ["src.moduleA.fileA"],
    )

    assert result == {"src.moduleA.fileA"}


def test_external_importee_sharing_root_module_prefix_is_added() -> None:
    """An external module that only shares the root module's name prefix must
    not be mistaken for an internal module (e.g. 'apprise' with root 'app')."""
    result = set(
        ImporteeModuleCalculator(
            Path("/dummy/project/app"), "app"
        ).calculate_importee_modules(
            [AbsoluteImport("app.moduleA.fileA", "apprise.core")],
            ["app.moduleA.fileA"],
        )
    )

    assert result == {"app.moduleA.fileA", "apprise.core", "apprise"}


def container_calculate_relative_naming(root_path, imports):
    """ImporteeModuleCalculator with module names carrying no prefix (relative module
    naming for a container root, i.e. root_module_name is empty)."""
    (root_path / "pkg_a").mkdir()
    (root_path / "top.py").touch()
    return set(
        ImporteeModuleCalculator(root_path, "").calculate_importee_modules(imports, [])
    )


def test_relative_naming_importee_under_root_is_not_added(tmp_path) -> None:
    result = container_calculate_relative_naming(
        tmp_path,
        [AbsoluteImport("X", "pkg_a.mod")],
    )

    assert result == set()


def test_relative_naming_top_level_module_file_importee_is_not_added(tmp_path) -> None:
    result = container_calculate_relative_naming(
        tmp_path,
        [AbsoluteImport("X", "top")],
    )

    assert result == set()


def test_relative_naming_external_importee_and_parents_are_added(tmp_path) -> None:
    result = container_calculate_relative_naming(
        tmp_path,
        [AbsoluteImport("X", "os.path")],
    )

    assert result == {"os.path", "os"}


def test_default_naming_container_root_importee_without_prefix_is_external(
    tmp_path,
) -> None:
    """With the default naming, container root module names are prefixed with the root
    directory's name, so an importee without that prefix is a genuine external module."""
    root_module_name = tmp_path.name

    result = set(
        ImporteeModuleCalculator(tmp_path, root_module_name).calculate_importee_modules(
            [AbsoluteImport(f"{root_module_name}.pkg_a.mod", "pkg_b.mod")],
            [],
        )
    )

    assert result == {"pkg_b.mod", "pkg_b"}


def test_default_naming_container_root_prefixed_importee_is_internal(tmp_path) -> None:
    root_module_name = tmp_path.name

    result = set(
        ImporteeModuleCalculator(tmp_path, root_module_name).calculate_importee_modules(
            [
                AbsoluteImport(
                    f"{root_module_name}.pkg_a.mod", f"{root_module_name}.top"
                )
            ],
            [],
        )
    )

    assert result == set()
