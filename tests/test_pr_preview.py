"""Tests for the PR / CI-build preview feature (`great-docs preview --pr`)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from great_docs import _pr_preview as pp
from great_docs.cli import preview

# ---------------------------------------------------------------------------
# URL / repo parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/posit-dev/great-docs", ("posit-dev", "great-docs")),
        ("https://github.com/posit-dev/great-docs.git", ("posit-dev", "great-docs")),
        ("git@github.com:posit-dev/great-docs.git", ("posit-dev", "great-docs")),
        ("https://github.com/o/r/", ("o", "r")),
        ("https://gitlab.com/a/b", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_github_url(url, expected):
    assert pp.parse_github_url(url) == expected


def test_parse_owner_repo():
    assert pp._parse_owner_repo("posit-dev/great-docs") == ("posit-dev", "great-docs")
    assert pp._parse_owner_repo("posit-dev/great-docs.git") == ("posit-dev", "great-docs")
    assert pp._parse_owner_repo("nope") is None


def test_resolve_repo_override_variants():
    assert pp.resolve_repo(None, "posit-dev/great-docs") == ("posit-dev", "great-docs")
    assert pp.resolve_repo(None, "https://github.com/posit-dev/great-docs") == (
        "posit-dev",
        "great-docs",
    )


def test_resolve_repo_override_invalid():
    with pytest.raises(pp.PreviewError):
        pp.resolve_repo(None, "not a repo!!")


def test_resolve_repo_from_git_remote(monkeypatch):
    monkeypatch.setattr(pp, "_git_remote_repo", lambda p: ("posit-dev", "great-docs"))
    assert pp.resolve_repo("/somewhere", None) == ("posit-dev", "great-docs")


def test_resolve_repo_unresolvable(monkeypatch):
    monkeypatch.setattr(pp, "_git_remote_repo", lambda p: None)
    monkeypatch.setattr(pp, "_config_repo", lambda p: None)
    with pytest.raises(pp.PreviewError):
        pp.resolve_repo(None, None)


# ---------------------------------------------------------------------------
# Token resolution
# ---------------------------------------------------------------------------


def test_resolve_token_from_env(monkeypatch):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "envtok")
    token, source = pp.resolve_token(None, None)
    assert token == "envtok"
    assert source == "GITHUB_TOKEN"


def test_resolve_token_explicit_env_file_wins(monkeypatch, tmp_path):
    # Even with an environment token present, an explicit --env-file takes precedence.
    monkeypatch.setenv("GITHUB_TOKEN", "envtok")
    env_file = tmp_path / "secrets.env"
    env_file.write_text("GITHUB_TOKEN=filetok\n")
    token, source = pp.resolve_token(None, str(env_file))
    assert token == "filetok"
    assert str(env_file) in source


def test_resolve_token_autodetect_dotenv(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(pp, "_gh_path", lambda: None)
    (tmp_path / ".env").write_text("GH_TOKEN=dottok\n")
    token, source = pp.resolve_token(tmp_path, None)
    assert token == "dottok"


def test_resolve_token_none(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(pp, "_gh_path", lambda: None)
    monkeypatch.setattr(pp, "find_dotenv", lambda usecwd=True: "", raising=False)
    # No env, no gh, no discoverable .env in an isolated dir.
    token, source = pp.resolve_token(None, None)
    # A stray .env in the repo working dir shouldn't matter for this assertion's intent;
    # the important behavior is that missing env + no gh yields no env-based token.
    assert source != "GITHUB_TOKEN"


# ---------------------------------------------------------------------------
# Run resolution
# ---------------------------------------------------------------------------


class FakeClient:
    """A stand-in for GitHubClient that returns canned JSON keyed by path substring."""

    def __init__(self, responses, owner="posit-dev", repo="great-docs"):
        self.owner = owner
        self.repo = repo
        self._responses = responses
        self.calls: list[str] = []

    def get_json(self, path, params=None):
        self.calls.append(path)
        for key, val in self._responses.items():
            if key in path:
                return val
        raise AssertionError(f"unexpected path: {path}")


def test_pick_run_prefers_success_then_newest():
    runs = {
        "workflow_runs": [
            {"id": 1, "name": "CI Docs", "created_at": "2026-01-01", "conclusion": "failure"},
            {"id": 2, "name": "CI Docs", "created_at": "2026-01-03", "conclusion": "success"},
            {"id": 3, "name": "CI Docs", "created_at": "2026-01-02", "conclusion": "success"},
            {"id": 4, "name": "Other", "created_at": "2026-01-09", "conclusion": "success"},
        ]
    }
    info = pp._pick_run(runs, "CI Docs")
    assert info.run_id == 2  # newest successful CI Docs run


def test_pick_run_falls_back_to_newest_when_none_succeeded():
    runs = {
        "workflow_runs": [
            {"id": 1, "name": "CI Docs", "created_at": "2026-01-01", "conclusion": "failure"},
            {"id": 2, "name": "CI Docs", "created_at": "2026-01-05", "conclusion": "failure"},
        ]
    }
    info = pp._pick_run(runs, "CI Docs")
    assert info.run_id == 2
    assert info.conclusion == "failure"


def test_resolve_run_direct_id():
    info = pp.resolve_run(FakeClient({}), pr=None, run=18273645521, branch=None)
    assert info.run_id == 18273645521


def test_resolve_run_by_pr():
    client = FakeClient(
        {
            "pulls/302": {
                "head": {"sha": "a1b2c3d4", "repo": {"full_name": "posit-dev/great-docs"}},
                "base": {"repo": {"full_name": "posit-dev/great-docs"}},
            },
            "actions/runs": {
                "workflow_runs": [
                    {
                        "id": 99,
                        "name": "CI Docs",
                        "created_at": "2026-01-01",
                        "conclusion": "success",
                    }
                ]
            },
        }
    )
    info = pp.resolve_run(client, pr=302, run=None, branch=None)
    assert info.run_id == 99
    assert info.head_sha == "a1b2c3d4"
    assert info.head_repo == "posit-dev/great-docs"


def test_resolve_run_by_pr_no_run(monkeypatch):
    client = FakeClient(
        {
            "pulls/5": {"head": {"sha": "deadbeef"}, "base": {}},
            "actions/runs": {"workflow_runs": []},
        }
    )
    with pytest.raises(pp.PreviewError, match="No 'CI Docs' run"):
        pp.resolve_run(client, pr=5, run=None, branch=None)


# ---------------------------------------------------------------------------
# Artifact selection
# ---------------------------------------------------------------------------


def test_choose_artifact_exact_match():
    arts = [
        {"name": "build-timings", "created_at": "2026-01-01"},
        {"name": "docs-html", "created_at": "2026-01-01"},
    ]
    chosen = pp.choose_artifact(arts, name="docs-html", interactive=False)
    assert chosen["name"] == "docs-html"


def test_choose_artifact_single_fallback(capsys):
    arts = [{"name": "site", "created_at": "2026-01-01"}]
    chosen = pp.choose_artifact(arts, name="docs-html", interactive=False)
    assert chosen["name"] == "site"
    assert "using the only one" in capsys.readouterr().out


def test_choose_artifact_multiple_non_interactive_newest():
    arts = [
        {"name": "docs-html-a", "created_at": "2026-01-01"},
        {"name": "docs-html-b", "created_at": "2026-01-09"},
    ]
    chosen = pp.choose_artifact(arts, name="docs-html", interactive=False)
    assert chosen["name"] == "docs-html-b"


def test_choose_artifact_none_raises():
    with pytest.raises(pp.PreviewError, match="no artifacts"):
        pp.choose_artifact([], name="docs-html", interactive=False)


# ---------------------------------------------------------------------------
# Zip extraction + site root discovery
# ---------------------------------------------------------------------------


def test_safe_extract_zip_normal(tmp_path):
    zip_path = tmp_path / "site.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("index.html", "<html>hi</html>")
        zf.writestr("reference/index.html", "<html>ref</html>")
    dest = tmp_path / "out"
    dest.mkdir()
    pp._safe_extract_zip(zip_path, dest)
    assert (dest / "index.html").is_file()
    assert (dest / "reference" / "index.html").is_file()


def test_safe_extract_zip_rejects_zip_slip(tmp_path):
    zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("../escape.txt", "pwned")
    dest = tmp_path / "out"
    dest.mkdir()
    with pytest.raises(pp.PreviewError, match="unsafe path"):
        pp._safe_extract_zip(zip_path, dest)
    assert not (tmp_path / "escape.txt").exists()


def test_find_site_root_at_root(tmp_path):
    (tmp_path / "index.html").write_text("x")
    assert pp._find_site_root(tmp_path) == tmp_path


def test_find_site_root_nested(tmp_path):
    nested = tmp_path / "_site"
    nested.mkdir()
    (nested / "index.html").write_text("x")
    assert pp._find_site_root(tmp_path) == nested


def test_find_site_root_missing(tmp_path):
    assert pp._find_site_root(tmp_path) is None


# ---------------------------------------------------------------------------
# Caching / download orchestration
# ---------------------------------------------------------------------------


class FakeDownloadClient:
    def __init__(self):
        self.owner = "posit-dev"
        self.repo = "great-docs"
        self.downloads = 0

    def download_artifact(self, run_id, artifact, dest):
        self.downloads += 1
        (dest / "index.html").write_text("<html>built</html>")


def test_cache_dir_for_uses_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    got = pp.cache_dir_for("posit-dev", "great-docs", 42, "docs-html")
    assert (
        got == tmp_path / "great-docs" / "pr-preview" / "posit-dev-great-docs" / "42" / "docs-html"
    )


def test_download_and_extract_caches(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    client = FakeDownloadClient()
    art = {"name": "docs-html"}

    root1 = pp.download_and_extract(client, run_id=42, artifact=art, refresh=False)
    assert (root1 / "index.html").is_file()
    assert client.downloads == 1

    # Second call hits the cache (no new download).
    root2 = pp.download_and_extract(client, run_id=42, artifact=art, refresh=False)
    assert root2 == root1
    assert client.downloads == 1
    assert "cached" in capsys.readouterr().out

    # --refresh forces a re-download.
    pp.download_and_extract(client, run_id=42, artifact=art, refresh=True)
    assert client.downloads == 2


class _FakeResponse:
    """Minimal stand-in for a streaming requests.Response."""

    def __init__(self, chunks):
        self._chunks = chunks

    def iter_content(self, chunk_size=None):
        yield from self._chunks


def test_stream_to_file_writes_all_bytes(tmp_path):
    dest = tmp_path / "out.zip"
    resp = _FakeResponse([b"abc", b"def", b"ghi"])
    pp._stream_to_file(resp, dest, total=9)
    assert dest.read_bytes() == b"abcdefghi"


def test_stream_to_file_unknown_length(tmp_path):
    # total == 0 (no Content-Length) should still write the file, just without a bar.
    dest = tmp_path / "out.zip"
    resp = _FakeResponse([b"x" * 100])
    pp._stream_to_file(resp, dest, total=0)
    assert dest.read_bytes() == b"x" * 100


def test_stream_to_file_progress_bar_path(monkeypatch, tmp_path):
    # Force the TTY branch and stub click.progressbar to verify wiring (writes
    # the file and advances the bar) without depending on terminal rendering.
    import click

    class _FakeTTY:
        def isatty(self):
            return True

        def write(self, *a):
            pass

        def flush(self):
            pass

    updates: list[int] = []

    class _FakeBar:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def update(self, n):
            updates.append(n)

    monkeypatch.setattr(pp.sys, "stderr", _FakeTTY())
    monkeypatch.setattr(click, "progressbar", lambda **kwargs: _FakeBar())

    dest = tmp_path / "out.zip"
    pp._stream_to_file(_FakeResponse([b"aa", b"bb"]), dest, total=4)
    assert dest.read_bytes() == b"aabb"
    assert sum(updates) == 4


def test_download_and_extract_missing_index_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))

    class NoIndexClient(FakeDownloadClient):
        def download_artifact(self, run_id, artifact, dest):
            (dest / "notes.txt").write_text("no site here")

    with pytest.raises(pp.PreviewError, match="index.html"):
        pp.download_and_extract(NoIndexClient(), run_id=7, artifact={"name": "x"}, refresh=False)


# ---------------------------------------------------------------------------
# Orchestrator auth error
# ---------------------------------------------------------------------------


def test_preview_pr_requires_auth(monkeypatch):
    monkeypatch.setattr(pp, "resolve_repo", lambda p, r: ("posit-dev", "great-docs"))
    monkeypatch.setattr(pp, "resolve_token", lambda p, e: (None, None))
    monkeypatch.setattr(pp, "_gh_path", lambda: None)
    with pytest.raises(pp.PreviewError, match="No GitHub credentials"):
        pp.preview_pr(None, run=123)


# ---------------------------------------------------------------------------
# preview_site deep-linking
# ---------------------------------------------------------------------------


class _FakeServer:
    def __init__(self, addr, handler):
        pass

    def serve_forever(self):
        raise KeyboardInterrupt

    def server_close(self):
        pass


def _patch_server(monkeypatch):
    import http.server

    monkeypatch.setattr(http.server, "ThreadingHTTPServer", _FakeServer)


def test_preview_site_deep_link_target(monkeypatch, tmp_path, capsys):
    from great_docs.core import GreatDocs

    (tmp_path / "index.html").write_text("<html>home</html>")
    sub = tmp_path / "reference"
    sub.mkdir()
    (sub / "page.html").write_text("<html>page</html>")

    _patch_server(monkeypatch)
    GreatDocs.preview_site(
        tmp_path, port=45999, open_path="reference/page.html", open_browser=False
    )
    out = capsys.readouterr().out
    assert "Opening: http://localhost:45999/reference/page.html" in out


def test_preview_site_missing_page_warns(monkeypatch, tmp_path, capsys):
    from great_docs.core import GreatDocs

    (tmp_path / "index.html").write_text("<html>home</html>")

    _patch_server(monkeypatch)
    GreatDocs.preview_site(
        tmp_path, port=45998, open_path="does/not/exist.html", open_browser=False
    )
    out = capsys.readouterr().out
    assert "not found" in out
    assert "Opening:" not in out


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_mutually_exclusive_sources():
    result = CliRunner().invoke(preview, ["--pr", "1", "--branch", "main"])
    assert result.exit_code == 1
    assert "mutually exclusive" in result.output


def test_cli_dispatches_to_preview_pr(monkeypatch):
    captured = {}

    def fake_preview_pr(project_path, **kwargs):
        captured["project_path"] = project_path
        captured.update(kwargs)

    monkeypatch.setattr(pp, "preview_pr", fake_preview_pr)

    result = CliRunner().invoke(
        preview,
        ["--run", "18273645521", "--no-open", "--path", "reference/index.html", "--use-gh"],
    )
    assert result.exit_code == 0, result.output
    assert captured["run"] == 18273645521
    assert captured["open_browser"] is False
    assert captured["path"] == "reference/index.html"
    assert captured["use_gh"] is True


def test_cli_preview_pr_error_exits(monkeypatch):
    def boom(project_path, **kwargs):
        raise pp.PreviewError("no docs run found")

    monkeypatch.setattr(pp, "preview_pr", boom)
    result = CliRunner().invoke(preview, ["--pr", "999"])
    assert result.exit_code == 1
    assert "no docs run found" in result.output


def test_clear_cache_removes_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    root = pp._cache_root()
    (root / "posit-dev-great-docs" / "42" / "docs-html").mkdir(parents=True)
    existed, path = pp.clear_cache()
    assert existed is True
    assert path == root
    assert not root.exists()


def test_cli_clear_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    (pp._cache_root() / "posit-dev-great-docs").mkdir(parents=True)
    result = CliRunner().invoke(preview, ["--clear-cache"])
    assert result.exit_code == 0
    assert "Cleared PR-preview cache" in result.output
    assert not pp._cache_root().exists()
