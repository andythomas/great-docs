"""
gdtest_rust_cli — Minimal Rust CLI project documentation.

Dimensions: Z1, F6, G1, H7
Focus: Rust CLI detection (Cargo.toml + src/main.rs layout), binary compilation,
       recursive --help extraction, and CLI reference page generation.
       No Python module; the site is driven entirely by the Rust CLI.
"""

SPEC = {
    "name": "gdtest_rust_cli",
    "description": "Rust CLI project with clap-style --help output",
    "dimensions": ["Z1", "F6", "G1", "H7"],
    # ── Project metadata ──────────────────────────────────────────────────────
    # No pyproject_toml: render_all.py will add a minimal one as a root barrier.
    # The real project identity comes from Cargo.toml.
    # ── Source files ──────────────────────────────────────────────────────────
    "files": {
        "Cargo.toml": """\
            [package]
            name = "hello"
            version = "0.1.0"
            edition = "2021"
        """,
        "src/main.rs": """\
            // Minimal CLI that emits clap-style --help output so great-docs CLI
            // reference generation can be exercised without external Rust dependencies.

            const ROOT_HELP: &str = "\\
            A minimal Rust CLI for testing great-docs documentation.

            Usage: hello [OPTIONS] [COMMAND]

            Commands:
              greet    Print a personalised greeting
              version  Print the version

            Options:
              -c, --config <PATH>  Config file path [default: hello.toml]
              -v, --verbose        Enable verbose output
              -h, --help           Print help
              -V, --version        Print version";

            const GREET_HELP: &str = "\\
            Print a personalised greeting to standard output.

            Usage: hello greet [OPTIONS]

            Options:
              -n, --name <NAME>  Name to greet [default: World]
              -h, --help         Print help";

            const VERSION_HELP: &str = "\\
            Print the version string and exit.

            Usage: hello version [OPTIONS]

            Options:
              -h, --help  Print help";

            fn main() {
                let args: Vec<String> = std::env::args().skip(1).collect();

                let has_help = args.iter().any(|a| a == "--help" || a == "-h");

                if args.is_empty() || has_help {
                    let sub = args.iter().find(|a| !a.starts_with('-'));
                    match sub.map(|s| s.as_str()) {
                        Some("greet") => println!("{}", GREET_HELP),
                        Some("version") => println!("{}", VERSION_HELP),
                        _ => println!("{}", ROOT_HELP),
                    }
                    return;
                }

                match args[0].as_str() {
                    "greet" => {
                        let mut name = "World".to_string();
                        let mut i = 1;
                        while i < args.len() {
                            if (args[i] == "--name" || args[i] == "-n") && i + 1 < args.len() {
                                name = args[i + 1].clone();
                                i += 2;
                            } else {
                                i += 1;
                            }
                        }
                        println!("Hello, {}!", name);
                    }
                    "version" => println!("hello 0.1.0"),
                    other => {
                        eprintln!("unknown command: {}", other);
                        std::process::exit(1);
                    }
                }
            }
        """,
        "README.md": """\
            # hello

            A minimal Rust CLI for testing great-docs Rust CLI documentation generation.

            ## Installation

            ```bash
            cargo install hello
            ```

            ## Usage

            ```bash
            hello greet --name World
            hello version
            ```
        """,
    },
    # ── great-docs config ─────────────────────────────────────────────────────
    # Providing config here means `great-docs init` is skipped; only `build` runs.
    "config": {
        "project_type": "rust",
        "rust_cli": {
            "enabled": True,
        },
        "mcp": {
            "enabled": False,
        },
    },
    # ── Expected outcomes ─────────────────────────────────────────────────────
    "expected": {
        # render_all.py writes a pyproject.toml root-barrier with the spec name,
        # so detected_name comes from that.
        "detected_name": "gdtest-rust-cli",
        # No Python module — pure Rust project.
        "detected_module": None,
        "has_user_guide": False,
        "has_license_page": False,
        "has_citation_page": False,
        "rust_cli_enabled": True,
        # Coverage levels this package does NOT participate in (no Python API).
        "coverage_exclude": [
            "nodoc",
            "bigcl",
            "ug",
            "supp",
            "hdg",
            "ref",
            "sig",
            "desc",
            "param",
            "pmatch",
            "ret",
            "refidx",
            "sechdg",
        ],
    },
}
