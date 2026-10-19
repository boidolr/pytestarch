"""Experimental architecture rules.

The rules provided in this subpackage are drafts of architecture checks. Their
API is not finalized yet and may change or be removed without notice. Feedback
on the currently offered rules is very welcome (see
https://github.com/zyskarch/pytestarch/issues/134 and
https://github.com/zyskarch/pytestarch/issues/71).
"""

from pytestarch.experimental.coupling import CouplingRule
from pytestarch.experimental.layered_architecture import (
    PredefinedLayeredArchitecture,
    layered_architecture,
)
from pytestarch.experimental.onion_architecture import (
    OnionArchitecture,
    onion_architecture,
)

__all__ = [
    "CouplingRule",
    "PredefinedLayeredArchitecture",
    "layered_architecture",
    "OnionArchitecture",
    "onion_architecture",
]
