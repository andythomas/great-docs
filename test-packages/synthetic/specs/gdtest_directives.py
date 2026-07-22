"""
gdtest_directives — all canonical Great Docs callout directives in one page

Dimensions: L3, L4
Focus: Canonical directives render as styled callouts without raw directive text.
"""

SPEC = {
    "name": "gdtest_directives",
    "description": "Tests all canonical Great Docs callout directives",
    "dimensions": ["L3", "L4"],
    "pyproject_toml": {
        "project": {
            "name": "gdtest-directives",
            "version": "0.1.0",
            "description": "Test canonical Great Docs directives",
        },
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
    },
    "files": {
        "gdtest_directives/__init__.py": '''\
            """Package exercising canonical Great Docs directives."""

            __version__ = "0.1.0"
            __all__ = ["process"]


            def process(data: list) -> list:
                """
                Process data using the current pipeline.

                Parameters
                ----------
                data
                    The data to process.

                Returns
                -------
                list
                    A processed copy.

                %versionadded 2.0

                %versionchanged 2.1
                    Returns a copy.

                %deprecated 3.0 Use `new_process` instead.

                %note Inline note.

                %warning
                    Multiline warning.

                    Preserve this paragraph.

                %caution Inline caution.
                %danger Inline danger.
                %important Inline important.
                %tip Inline tip.
                %hint Inline hint.
                """
                return list(data)
        ''',
        "README.md": """\
            # gdtest-directives

            Tests canonical Great Docs directives.
        """,
    },
    "expected": {
        "detected_name": "gdtest-directives",
        "detected_module": "gdtest_directives",
        "detected_parser": "numpy",
        "export_names": ["process"],
        "num_exports": 1,
        "coverage_exclude": ["nodoc", "bigcl", "ug", "supp", "sechdg", "sbsec", "hdg"],
    },
}
