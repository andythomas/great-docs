"""
gdtest_cli_typer — Typer CLI documentation.

Dimensions: A1, B1, C1, D1, E1+E6, F6, G1, H7
Focus: Typer CLI discovery and documentation generation.

Typer vendors its own copy of Click, so the app object is not a plain
`click.Command`; great-docs converts it via `typer.main.get_command` and then
reuses the same Click introspection path. The app has a nested sub-app
(`add_typer`) so the grouped/nested sidebar structure is exercised too.
"""

SPEC = {
    "name": "gdtest_cli_typer",
    "description": "Typer CLI with a nested sub-app and CLI docs enabled",
    "dimensions": ["A1", "B1", "C1", "D1", "E1", "E6", "F6", "G1", "H7"],
    "pyproject_toml": {
        "project": {
            "name": "gdtest-cli-typer",
            "version": "0.1.0",
            "description": "A package with a Typer CLI",
            "scripts": {
                "gdtest-typer": "gdtest_cli_typer.cli:app",
            },
        },
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
    },
    "files": {
        "gdtest_cli_typer/__init__.py": '''\
            """A package with Typer CLI support."""

            __version__ = "0.1.0"
            __all__ = ["Formatter", "format_text"]


            class Formatter:
                """
                A text formatter.

                Parameters
                ----------
                style
                    The formatting style to use.
                """

                def __init__(self, style: str = "default"):
                    self.style = style

                def apply(self, text: str) -> str:
                    """
                    Apply formatting to text.

                    Parameters
                    ----------
                    text
                        The text to format.

                    Returns
                    -------
                    str
                        Formatted text.
                    """
                    return text


            def format_text(text: str, style: str = "default") -> str:
                """
                Format text with a given style.

                Parameters
                ----------
                text
                    The text to format.
                style
                    The style to apply.

                Returns
                -------
                str
                    Formatted text.
                """
                return Formatter(style).apply(text)
        ''',
        "gdtest_cli_typer/cli.py": '''\
            """CLI entry point using Typer."""

            import typer

            app = typer.Typer(help="Format and manage text with the gdtest-cli-typer tool.")

            db_app = typer.Typer(help="Manage the formatting cache database.")
            app.add_typer(db_app, name="db")


            @app.command()
            def format(
                text: str,
                style: str = typer.Option("default", "--style", "-s", help="Formatting style."),
                verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output."),
            ) -> None:
                """Format TEXT using the configured formatter."""
                if verbose:
                    typer.echo(f"Formatting with style: {style}")
                typer.echo(text)


            @app.command()
            def version() -> None:
                """Show the tool version and exit."""
                typer.echo("0.1.0")


            @db_app.command()
            def clear(force: bool = typer.Option(False, "--force", help="Skip confirmation.")) -> None:
                """Clear the formatting cache."""
                typer.echo("cleared" if force else "confirm?")


            @db_app.command()
            def info() -> None:
                """Show cache database info."""
                typer.echo("cache info")
        ''',
        "README.md": """\
            # gdtest-cli-typer

            A test package with Typer CLI support.
        """,
    },
    "config": {
        "cli": {
            "enabled": True,
        },
    },
    "expected": {
        "detected_name": "gdtest-cli-typer",
        "detected_module": "gdtest_cli_typer",
        "detected_parser": "numpy",
        "export_names": ["Formatter", "format_text"],
        "num_exports": 2,
        "section_titles": ["Classes", "Functions"],
        "has_user_guide": False,
        "cli_enabled": True,
        "cli_has_groups": True,
        "cli_group_names": ["db"],
        "coverage_exclude": ["nodoc", "bigcl", "ug", "supp", "hdg"],
    },
}
