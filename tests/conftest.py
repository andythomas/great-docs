"""
Prepare rendered citation fixtures before test collection

A fresh checkout has no rendered Gauntlet sites. Build the citation fixtures
before collection so the rendered-HTML assertions run without a complete
`make hub-build`.
"""

from __future__ import annotations

import warnings

import pytest

from tests.gauntlet_sites import RENDERED_DIR


def pytest_configure(config: pytest.Config) -> None:
    """
    Prepare the citation Gauntlet sites before collection

    The rendered-output tests determine their parameters during import, before
    a fixture could build the required sites. Existing sites remain unchanged.

    Environmental failures warn and leave the affected sites unavailable, so
    their rendered-output tests skip. These failures include unavailable
    imports, invalid Gauntlet specifications, and filesystem errors while
    managing the sentinel lock. The site builder handles render failures for
    each package. Other exceptions abort the session because they indicate a
    defect in the fixture builder.

    Parameters
    ----------
    config
        The pytest config object. Unused.

    """
    try:
        from tests import gauntlet_sites

        if not gauntlet_sites.quarto_available():
            return
        gauntlet_sites.ensure_sites(RENDERED_DIR, gauntlet_sites.CITATION_SITES)
    except (OSError, ImportError, ValueError, KeyError) as exc:
        # Preserve the rest of the test session when the optional rendered
        # fixtures are unavailable. Unexpected builder defects still propagate.
        warnings.warn(f"could not prepare Gauntlet citation sites: {exc}", stacklevel=2)
