# Coupling Checks (experimental)

⚠ This rule is still a draft: its API is not finalized yet and may change or be
removed without notice. It therefore lives in `pytestarch.experimental`. Feedback
and suggestions are welcome - create a new
[issue](https://github.com/zyskarch/pytestarch/issues/new).

The coupling rule limits how strongly modules are connected to the rest of the
codebase:

- **Efferent coupling (Ce)**: the number of distinct modules a module depends on.
- **Afferent coupling (Ca)**: the number of distinct modules that depend on it.

Both metrics count direct imports only. They are not transitive and they count
modules, not individual import statements.

## Usage

```python
from pytestarch import get_evaluable_architecture
from pytestarch.experimental import CouplingRule

evaluable = get_evaluable_architecture(root_path, module_path)

rule = (
    CouplingRule()
    .modules_that()
    .are_named("my_project.services")
    .should_have_max_efferent_coupling(5)
    .should_have_max_afferent_coupling(10)
)

rule.assert_applies(evaluable)
```

Either threshold can be omitted, but at least one is required. The rule supports
the same module specifications as the regular rule language:

```python
.modules_that().are_named("my_project.services")
.modules_that().are_named(["my_project.services", "my_project.api"])
.modules_that().are_sub_modules_of("my_project.services")
.modules_that().have_name_matching(r".*\.services$")
```

## What counts as coupling

A module includes its submodules. Its parent modules and other ancestors are
treated as internal as well. For `my_project.services`:

- `my_project`, `my_project.services`, and `my_project.services.orders` are
  internal.
- `my_project.model`, `my_project.persistence`, and third-party modules are
  external.

Only direct import edges that cross this boundary are counted. Parent/child
hierarchy edges and imports between a module and its own submodules are ignored.

## Granularity

Coupling counts distinct graph nodes. If a module imports both
`my_project.model.user` and `my_project.model.order`, its efferent coupling is
`2`, not `1`. This is the module-level analogue of the package metric, which
counts classes.

Use the `level_limit` parameter of `get_evaluable_architecture` to evaluate a
coarser graph:

```python
evaluable = get_evaluable_architecture(
    root_path,
    module_path,
    level_limit=1,
)
```

## Notes

- Imports are direct only. A dependency chain `A -> B -> C` contributes `1` to
  `A`'s efferent coupling (`B`), not `2`.
- Imports from multiple submodules to the same external module count once.
- External dependencies are only visible if they are part of the evaluable. By
  default, `exclude_external_libraries=True` removes them, so pass
  `exclude_external_libraries=False` to include them in the coupling counts.
- Files excluded during graph generation also do not contribute to coupling.
- `are_sub_modules_of(X)` checks the strict submodules of `X` as one group; `X`
  itself is internal and is not checked, and each submodule is not checked
  separately.
- `have_name_matching(...)` may match a parent module and its submodules. Each
  match is checked independently, so overlapping subjects can count the same
  import more than once.
- Reusing a `CouplingRule` object is supported; it is not mutated by
  `assert_applies`.

## Violation messages

If a threshold is exceeded, the assertion message names the module, the metric,
the actual value, the maximum, and the coupled modules:

```text
"my_project.services" has an efferent coupling of 7, but the maximum is 5. Coupled modules: "my_project.db", "my_project.http".
```

For a group subject, the message uses `Sub modules of`:

```text
Sub modules of "my_project.services" have an afferent coupling of 12, but the maximum is 10. Coupled modules: "my_project.api", "my_project.web".
```
