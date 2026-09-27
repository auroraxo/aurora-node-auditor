"""Single source of truth for the running package version.

This module deliberately imports nothing from the ``auditor`` package at
module level so it can be imported safely while the package ``__init__``
is still executing (circular-import free). The package attribute is the
primary source; installed distribution metadata is the secondary source;
``"unknown"`` is the last resort. No hardcoded release literals live here
- they are what this module exists to eliminate.
"""

from typing import Optional as _Optional

_DIST_NAME = "aurora-node-auditor"
_UNKNOWN = "unknown"


def get_version(primary: _Optional[str] = None) -> str:
    """Return the running package version, never a stale literal.

    Args:
        primary: Optional pre-resolved version (e.g. ``auditor.__version__``)
            to try first. When omitted the package attribute is resolved
            lazily, which keeps this function usable from any submodule.
    """
    if primary is not None:
        return str(primary)
    try:
        from auditor import __version__
        return str(__version__)
    except Exception:
        pass
    try:
        from importlib.metadata import version
        return version(_DIST_NAME)
    except Exception:
        return _UNKNOWN
