"""Tests targeting great_docs/_versioning.py."""

from __future__ import annotations


from great_docs._versioning import (
    BadgeExpiry,
    VersionEntry,
    _find_entry,
    _parse_version_tuple,
    _resolve_version_str,
    evaluate_version_expr,
    extract_page_versions,
    is_badge_expired,
    is_page_upcoming,
)


def _versions(*tags, **kwargs):
    """Build a list of VersionEntry objects from tag strings."""
    entries = []
    for i, tag in enumerate(tags):
        if isinstance(tag, dict):
            entries.append(VersionEntry(_index=i, **tag))
        else:
            entries.append(VersionEntry(tag=tag, label=tag, _index=i, **kwargs))
    return entries


# ---------------------------------------------------------------------------
# _parse_version_tuple returns None on non-numeric
# ---------------------------------------------------------------------------


class TestParseVersionTuple:
    def test_valid_version(self):
        assert _parse_version_tuple("1.2.3") == (1, 2, 3)

    def test_version_with_v_prefix(self):
        assert _parse_version_tuple("v0.5") == (0, 5)

    def test_non_numeric_returns_none(self):
        """Non-numeric version string returns None."""
        assert _parse_version_tuple("dev") is None

    def test_partial_non_numeric_returns_none(self):
        assert _parse_version_tuple("1.2.beta") is None


# ---------------------------------------------------------------------------
# _resolve_version_str — alt prefix fallback
# ---------------------------------------------------------------------------


class TestResolveVersionStr:
    def test_exact_match(self):
        versions = _versions("0.9", "0.8")

        assert _resolve_version_str("0.9", versions) == "0.9"

    def test_v_prefix_fallback(self):
        """Tag with 'v' prefix tries without it."""
        versions = _versions("0.9", "0.8")

        # Looking for "v0.9" which has alt "0.9"
        assert _resolve_version_str("v0.9", versions) == "0.9"

    def test_no_match_returns_tag(self):
        """When no version matches, returns the original tag."""
        versions = _versions("0.9", "0.8")

        assert _resolve_version_str("unknown", versions) == "unknown"

    def test_version_field_match(self):
        """Match via the version field of a VersionEntry."""
        versions = [
            VersionEntry(tag="dev", label="dev", version="0.10", _index=0),
            VersionEntry(tag="0.9", label="0.9", _index=1),
        ]

        assert _resolve_version_str("0.10", versions) == "0.10"


# ---------------------------------------------------------------------------
# evaluate_version_expr edge cases
# ---------------------------------------------------------------------------


class TestEvaluateVersionExprEdgeCases:
    def test_or_mode_no_regex_match_skipped(self):
        """In OR mode, empty part doesn't match regex and is skipped."""
        versions = _versions("0.9", "0.8", "0.7")

        # Leading comma → empty part first, then "0.9" matches
        result = evaluate_version_expr(",0.9", "0.9", versions)

        assert result is True

    def test_and_mode_no_regex_match_returns_false(self):
        """In AND mode, empty part doesn't match regex → returns False."""
        versions = _versions("0.9", "0.8", "0.7")

        # ">=0.8," has trailing comma → empty part in AND mode → return False
        result = evaluate_version_expr(">=0.8,", "0.9", versions)

        assert result is False

    def test_and_mode_equality_mismatch(self):
        """AND mode equality check returns False when idx differs."""
        versions = _versions("0.9", "0.8", "0.7")

        # Bare "0.8" in AND context (mixed with operator): target=0.9, ref=0.8 → mismatch
        result = evaluate_version_expr("=0.8", "0.9", versions)

        assert result is False

    def test_semver_fallback_unparseable_returns_false(self):
        """When ref version is not in list and tag can't be parsed, returns False."""
        versions = _versions("dev", "0.9")
        versions[0].version = None

        # ">=alpha" — "alpha" not in versions, can't parse as tuple
        result = evaluate_version_expr(">=alpha", "dev", versions)

        assert result is False

    def test_semver_fallback_gt_operator(self):
        """Semver fallback with '>' operator."""
        # Only 0.9 configured; 0.5 not in the list, so semver fallback kicks in
        versions = _versions("0.9")

        # target=0.9, ref=0.5, op=">": 0.9 > 0.5 is True → constraint satisfied
        result = evaluate_version_expr(">0.5", "0.9", versions)

        assert result is True

    def test_semver_fallback_gt_fails(self):
        """Semver fallback '>' returns False when target <= ref."""
        versions = _versions("0.5")
        result = evaluate_version_expr(">0.9", "0.5", versions)

        assert result is False


# ---------------------------------------------------------------------------
# is_badge_expired branches
# ---------------------------------------------------------------------------


class TestIsBadgeExpired:
    def test_minor_releases_badge_not_found(self):
        """minor_releases mode returns False when badge version not resolved."""
        versions = _versions("0.9", "0.8")
        target = versions[0]
        expiry = BadgeExpiry(mode="minor_releases", value=1)

        # Badge version "unknown" won't resolve
        assert is_badge_expired("unknown", target, versions, expiry) is False

    def test_date_mode_invalid_date(self):
        """date mode with invalid date returns False."""
        versions = _versions("0.9")
        target = versions[0]
        expiry = BadgeExpiry(mode="date", value="not-a-date")

        assert is_badge_expired("0.9", target, versions, expiry) is False

    def test_date_mode_future_date(self):
        """date mode with future date returns False."""
        versions = _versions("0.9")
        target = versions[0]
        expiry = BadgeExpiry(mode="date", value="2099-01-01")

        assert is_badge_expired("0.9", target, versions, expiry) is False

    def test_date_mode_past_date(self):
        """date mode with past date returns True."""
        versions = _versions("0.9")
        target = versions[0]
        expiry = BadgeExpiry(mode="date", value="2020-01-01")

        assert is_badge_expired("0.9", target, versions, expiry) is True

    def test_days_mode_invalid_release_date(self):
        """days mode with unparseable released date returns False."""
        versions = [VersionEntry(tag="0.9", label="0.9", released="not-a-date", _index=0)]
        target = versions[0]
        expiry = BadgeExpiry(mode="days", value=1)

        assert is_badge_expired("0.9", target, versions, expiry) is False

    def test_days_mode_recently_released(self):
        """days mode returns False when badge released recently."""
        versions = [VersionEntry(tag="0.9", label="0.9", released="2099-01-01", _index=0)]
        target = versions[0]
        expiry = BadgeExpiry(mode="days", value=30)

        assert is_badge_expired("0.9", target, versions, expiry) is False

    def test_days_mode_old_release(self):
        """days mode returns True when badge released long ago."""
        versions = [VersionEntry(tag="0.9", label="0.9", released="2020-01-01", _index=0)]
        target = versions[0]
        expiry = BadgeExpiry(mode="days", value=30)

        assert is_badge_expired("0.9", target, versions, expiry) is True

    def test_version_mode_threshold_not_found(self):
        """version mode returns False when threshold version not resolved."""
        versions = _versions("0.9", "0.8")
        target = versions[0]
        expiry = BadgeExpiry(mode="version", value="nonexistent")

        assert is_badge_expired("0.9", target, versions, expiry) is False

    def test_unknown_mode_returns_false(self):
        """Unknown expiry mode falls through to return False."""
        versions = _versions("0.9")
        target = versions[0]
        expiry = BadgeExpiry(mode="unknown_mode", value=1)

        assert is_badge_expired("0.9", target, versions, expiry) is False


# ---------------------------------------------------------------------------
# _find_entry fallback paths
# ---------------------------------------------------------------------------


class TestFindEntry:
    def test_exact_match(self):
        versions = _versions("0.9", "0.8")

        assert _find_entry("0.9", versions) == versions[0]

    def test_v_prefix_fallback(self):
        """Finds entry by stripping/adding 'v' prefix."""
        versions = _versions("v1.0", "v0.9")
        result = _find_entry("1.0", versions)

        assert result == versions[0]

    def test_version_field_fallback(self):
        """Finds entry via the version field."""
        versions = [
            VersionEntry(tag="dev", label="dev", version="0.10", _index=0),
            VersionEntry(tag="0.9", label="0.9", _index=1),
        ]
        result = _find_entry("0.10", versions)

        assert result == versions[0]

    def test_not_found_returns_none(self):
        versions = _versions("0.9")

        assert _find_entry("nonexistent", versions) is None


# ---------------------------------------------------------------------------
# extract_page_versions — stops at next YAML key
# ---------------------------------------------------------------------------


class TestExtractPageVersions:
    def test_stops_at_next_yaml_key(self):
        """Stops reading list items when next top-level key encountered."""
        content = "---\nversions:\n  - 0.9\n  - 0.8\ntitle: Hello\n---\n# Content\n"
        result = extract_page_versions(content)

        assert result == ["0.9", "0.8"]

    def test_no_versions_key_returns_none(self):
        content = "---\ntitle: Hello\n---\n# Content\n"
        result = extract_page_versions(content)

        assert result is None


# ---------------------------------------------------------------------------
# is_page_upcoming — no matched versions returns False
# ---------------------------------------------------------------------------


class TestIsPageUpcoming:
    def test_no_matched_versions_returns_false(self):
        """When page versions don't match any entry, returns False."""
        versions = _versions("0.9", "0.8")

        # Page targets "0.5" which doesn't exist
        content = "---\nversions:\n  - 0.5\n---\n# Content\n"

        assert is_page_upcoming(content, versions) is False

    def test_all_prerelease_returns_true(self):
        """Page matching only prerelease versions is upcoming."""
        versions = [
            VersionEntry(tag="dev", label="dev", prerelease=True, _index=0),
            VersionEntry(tag="0.9", label="0.9", _index=1),
        ]
        content = "---\nversions:\n  - dev\n---\n# Content\n"

        assert is_page_upcoming(content, versions) is True

    def test_mixed_versions_not_upcoming(self):
        """Page matching both release and prerelease is not upcoming."""
        versions = [
            VersionEntry(tag="dev", label="dev", prerelease=True, _index=0),
            VersionEntry(tag="0.9", label="0.9", _index=1),
        ]
        content = "---\nversions:\n  - dev\n  - 0.9\n---\n# Content\n"

        assert is_page_upcoming(content, versions) is False
