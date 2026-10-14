from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from pytestarch.eval_structure.types import Import


class ImporteeModuleCalculator:
    """Adds all parent modules of imported modules if they are not yet part of the modules list."""

    def __init__(self, root_path: Path, root_module_name: str) -> None:
        """
        Args:
            root_path: root directory of the scanned source code
            root_module_name: name of the Python module all module names of the scan
                are prefixed with. Empty only if module names are derived relative to
                the root without a prefix (module_naming="relative" for a root
                directory without __init__.py).
        """
        self._root_path = root_path
        self._root_module_name = root_module_name

    def calculate_importee_modules(
        self,
        imports: Sequence[Import],
        all_modules: list[str],
    ) -> list[str]:
        """For all imported modules: Calculate parent modules and add them to the list of existing modules if they
        are not already part of this list. This mainly applies to external dependencies.

        Args:
            imports:
            all_modules:

        Returns:
            all modules extended by parent modules of imported modules
        """
        extended_modules = set(all_modules)

        for imp in imports:
            importee = imp.importee()

            if not self._is_internal_importee(importee):
                extended_modules.update(self._calculate_parent_modules(imp))

        return list(extended_modules)

    def _is_internal_importee(self, importee: str) -> bool:
        """An importee belongs to the scanned root if it is a submodule of the root
        module. Only if module names carry no root prefix at all (relative module
        naming for a container root), an importee whose top level module exists as a
        directory or module file under the root path is also considered internal - in
        this mode, importees that belong under the root (e.g. 'package2' in 'from
        package2 import module2' when the root is a 'src' directory) must not be
        treated as external dependencies, as they are part of the scanned source code.

        In the default (root dir) naming, absolute imports written root-relative are
        resolved to their prefixed names by the converter before they end up here, so
        an importee without the root module name prefix is genuinely external.
        """
        if self._root_module_name:
            return importee == self._root_module_name or importee.startswith(
                f"{self._root_module_name}."
            )

        first_segment = importee.split(".")[0]
        return (self._root_path / first_segment).is_dir() or (
            self._root_path / f"{first_segment}.py"
        ).is_file()

    def _calculate_parent_modules(self, imp: Import) -> set[str]:
        modules = {imp.importee()}
        modules.update(imp.importee_parent_modules())

        return modules
