"""
Reference pages with site-wide breadcrumbs disabled

Dimensions: Q1
Focus: Verify that API object pages and the index retain an API navigation
       label and one `h1` when `bread-crumbs: false` removes breadcrumb markup.
"""

SPEC = {
    "name": "gdtest_no_breadcrumbs",
    "description": "API reference pages with site-wide breadcrumbs disabled",
    "dimensions": ["Q1"],
    # ── Project metadata ─────────────────────────────────────────────
    "pyproject_toml": {
        "project": {
            "name": "gdtest-no-breadcrumbs",
            "version": "0.1.0",
            "description": "Synthetic package with breadcrumbs disabled site-wide",
        },
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
    },
    # ── great-docs.yml ───────────────────────────────────────────────
    "config": {
        "site": {"bread-crumbs": False},
    },
    # ── Source files ──────────────────────────────────────────────────
    "files": {
        "gdtest_no_breadcrumbs/__init__.py": '''\
            """Synthetic package with breadcrumbs disabled site-wide"""

            __version__ = "0.1.0"
            __all__ = ["greet", "add"]


            def greet(name: str) -> str:
                """
                Return a greeting for a name

                Parameters
                ----------
                name
                    Name to greet.

                Returns
                -------
                Greeting string.
                """
                return f"Hello, {name}!"


            def add(a: int, b: int) -> int:
                """
                Add two numbers

                Parameters
                ----------
                a
                    First number.
                b
                    Second number.

                Returns
                -------
                Sum of `a` and `b`.
                """
                return a + b
        ''',
        "README.md": """\
            # gdtest-no-breadcrumbs

            Exercise reference pages with breadcrumbs disabled site-wide.

            ## Installation

            ```bash
            pip install gdtest-no-breadcrumbs
            ```

            ## Usage

            ```python
            from gdtest_no_breadcrumbs import greet, add

            greet("World")
            add(1, 2)
            ```
        """,
    },
    # ── Expected outcomes ─────────────────────────────────────────────
    "expected": {
        "detected_name": "gdtest-no-breadcrumbs",
        "detected_module": "gdtest_no_breadcrumbs",
        "detected_parser": "numpy",
        "export_names": ["greet", "add"],
        "num_exports": 2,
        "section_titles": ["Functions"],
        "has_user_guide": False,
        "has_license_page": False,
        "has_citation_page": False,
        "coverage_exclude": ["nodoc", "bigcl", "ug", "supp"],
    },
}
