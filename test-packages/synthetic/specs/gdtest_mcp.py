"""
Rendered MCP reference fixture
"""

SPEC = {
    "name": "gdtest_mcp",
    "description": "Reference pages for every MCP object category",
    "dimensions": ["A1", "B1", "C1", "D4", "E6", "F6", "G1", "H7"],
    "pyproject_toml": {
        "project": {
            "name": "gdtest-mcp",
            "version": "0.1.0",
            "description": "Synthetic MCP reference package",
        },
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
    },
    "files": {
        "gdtest_mcp/__init__.py": '''\
            """Synthetic package for rendered MCP reference coverage"""

            __version__ = "0.1.0"
            __all__ = []
        ''',
        "gdtest_mcp/server.py": "from great_docs.mcp import server\n",
        "README.md": """\
            # gdtest-mcp

            Exercise rendered documentation for every MCP object category.
        """,
    },
    "config": {
        "exclude": ["server"],
        "mcp": {
            "enabled": True,
            "module": "gdtest_mcp.server",
            "server_var": "server",
            "name": "GDG MCP Server",
        },
    },
    "expected": {
        "detected_name": "gdtest-mcp",
        "detected_module": "gdtest_mcp",
        "detected_parser": "numpy",
        "has_user_guide": False,
        "mcp_enabled": True,
        "coverage_exclude": [
            "ref",
            "nodoc",
            "bigcl",
            "ug",
            "supp",
            "title",
            "badge",
            "sig",
            "desc",
            "param",
            "pmatch",
            "ret",
            "refidx",
            "sechdg",
            "sbar",
            "sbsec",
            "hdg",
        ],
    },
}
