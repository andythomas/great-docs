// Minimal CLI that emits clap-style --help output so great-docs parsing
// helpers can be exercised without external Rust dependencies.

const ROOT_HELP: &str = "\
A minimal Rust CLI fixture for great-docs testing.

Usage: hello [OPTIONS] [COMMAND]

Commands:
  greet    Print a personalised greeting
  version  Print the version

Options:
  -c, --config <PATH>  Config file path [default: hello.toml]
  -v, --verbose        Enable verbose output
  -h, --help           Print help
  -V, --version        Print version";

const GREET_HELP: &str = "\
Print a personalised greeting to standard output.

Usage: hello greet [OPTIONS]

Options:
  -n, --name <NAME>  Name to greet [default: World]
  -h, --help         Print help";

const VERSION_HELP: &str = "\
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
