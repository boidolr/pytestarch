from __future__ import annotations

from pytestarch.eval_structure_generation.file_import.import_types import (
    AbsoluteImport,
    RelativeImport,
)


def test_parent_modules_as_expected() -> None:
    imp = AbsoluteImport("test.test1.test2", "importee.importee2")

    assert set(imp.importer_parent_modules()) == {"test", "test.test1"}
    assert set(imp.importee_parent_modules()) == {"importee"}


def test_relative_import_parent_modules_as_expected() -> None:
    imp = RelativeImport("test.test1.test2", "importee", "importee2", 1)

    assert set(imp.importer_parent_modules()) == {"test", "test.test1"}
    assert set(imp.importee_parent_modules()) == {
        "test",
        "test.test1",
        "test.test1.importee",
    }


def test_relative_import_without_module_and_name_is_the_base_package() -> None:
    """The bare 'from . import <name>' form imports the containing package as
    well; an import without module and name represents exactly that package."""

    imp = RelativeImport("test.test1.test2", None, None, 1)

    assert imp.importee() == "test.test1"
    assert set(imp.importee_parent_modules()) == {"test"}

    imp_level_2 = RelativeImport("test.test1.test2", None, None, 2)

    assert imp_level_2.importee() == "test"
