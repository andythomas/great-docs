DEFAULT_CONFIG: dict[str, Any] = {
    # Module name (importable name, if different from project name)
    # e.g., project 'py-yaml12' might have module 'yaml12'
    "module": None,
    # Display name for the site (used in navbar/title)
    # If not provided, uses the package name as-is
    "display_name": None,
    # Project type — describes the primary ecosystem(s) the project belongs to.
    # Controls which ecosystem-specific links and features are active by default.
    #   "python"          — Python package (default); enables PyPI link
    #   "go"              — Go CLI/library; disables PyPI link by default
    #   ["python", "go"]  — mixed project (e.g., Python package that ships a Go sidecar)
    "project_type": "python",
    # Docstring parser format
    "parser": "numpy",  # "numpy" (default), "google", or "sphinx"
    # Dynamic introspection mode for API reference generation
    "dynamic": True,  # True (default) or False for packages with cyclic aliases
    # Jupyter kernel for executing code cells
    "jupyter": "python3",  # Default kernel for Quarto computations
    # API discovery settings
    "exclude": [],
    "auto_include": [],  # Names to force-include even if they match AUTO_EXCLUDE
    "no_auto_exclude": False,  # Bypass the built-in AUTO_EXCLUDE list entirely
    # PyPI link
    # True (default): auto-detect package name and link to pypi.org
    # False: disable the PyPI link entirely
    # str: custom package index URL (e.g., "https://artifactory.example.com/packages/my-pkg")
    "pypi": True,
    # GitHub integration
    "repo": None,  # GitHub repository URL override (e.g., "https://github.com/owner/repo")
    # Site URL: the canonical address of the deployed documentation site.
    # Used for skills page install commands, .well-known/ discovery, sitemaps,
    # and subdirectory deployments. Also sets website.site-url in _quarto.yml.
    "site_url": None,
    "github_style": "widget",  # "widget" (shows stars) or "icon"
    # Source link configuration
    "source": {
        "enabled": True,
        "branch": None,  # Auto-detect from git
        "path": None,  # Auto-detect
        "placement": "usage",  # "usage" (default) or "title"
    },
    # Sidebar filter configuration
    "sidebar_filter": {
        "enabled": True,
        "min_items": 20,
    },
    # CLI documentation configuration
    "cli": {
        "enabled": False,
        "module": None,
        "name": None,
    },
    # Go CLI documentation configuration
    # Builds the Go binary and extracts the command tree via --help to generate
    # a CLI reference section.  Works with any Go CLI (Cobra, urfave/cli, etc.)
    # as long as the binary supports --help on subcommands.
    "go_cli": {
        "enabled": False,
    },
    # MCP server documentation configuration
    # Auto-generates reference pages from MCP server tool/resource/prompt definitions.
    # None/False: disabled (default)
    # dict: {"enabled": True, "module": "package.mcp", ...}
    "mcp": {
        "enabled": True,
        "module": None,  # Importable module path containing the MCP server (e.g., "sweet.mcp")
        "server_var": None,  # Variable name of the Server instance (auto-detected if None)
        "name": None,  # Display name override (defaults to server name)
        "categories": {},  # Manual tool categories: {"Category Name": ["tool_a", "tool_b"]}
    },
    # Dark mode toggle
    "dark_mode_toggle": True,
    # Authors (rich author metadata)
    "authors": [],
    # Funding organization (copyright holder, funder)
    # Example: {"name": "Posit Software, PBC", "roles": ["Copyright holder", "funder"], "ror": "https://ror.org/03wc8by49"}
    "funding": None,
    # Site settings (forwarded to _quarto.yml format.html)
    "site": {
        "theme": "flatly",
        "toc": True,
        "toc-depth": 2,
        "html-math-method": "katex",
        # Language for UI text (BCP 47 code, e.g., "en", "fr", "de", "ja", "zh-Hans")
        # Translates navbar labels, widget text, tooltips, and accessibility labels
        "language": "en",
        # Page metadata timestamps
        "show_dates": False,  # Display creation/modification dates in footer
        "date_format": "%B %d, %Y",  # Python strftime format (e.g., "March 24, 2026")
        "show_author": True,  # Show author attribution when show_dates is enabled
        "show_security": True,  # Show security policy page when SECURITY.md exists
    },
    # Team author (catch-all for auto-generated pages when authorship is shown)
    # Example: {"name": "Great Tables Team", "image": "assets/team-avatar.png", "url": "https://..."}
    "team_author": None,
    # Changelog configuration (from GitHub Releases)
    "changelog": {
        "enabled": True,
        "max_releases": 50,
    },
    # Custom sections (generic page groups: examples, tutorials, blog, etc.)
    # Each entry: {"title": str, "dir": str, "index": bool, "index_columns": int,
    #              "navbar_after": str | None}
    "sections": [],
    # Custom static HTML pages.
    # None: auto-discover from project_root/custom/
    # False: disable custom page discovery entirely
    # str: one source directory, output defaults to its basename
    # dict: {"dir": str, "output": str | None}
    # list[str | dict]: multiple source directories
    "custom_pages": None,
    # Homepage mode
    # "index" (default): separate homepage from README / index source
    # "user_guide": first user-guide page becomes the landing page
    "homepage": "index",
    # User Guide configuration
    # If None, auto-discovers from user_guide/ directory
    # If a string, uses that as the directory path
    # If a list of section dicts, uses explicit ordering (overrides frontmatter sections)
    "user_guide": None,
    # API Reference configuration (explicit section ordering)
    # If not provided, auto-generates sections from discovered exports
    "reference": [],
    # Control whether class methods get their own pages or stay inline.
    # true: always inline methods on the class page (never split)
    # false: always give methods their own pages (always split)
    # int: inline up to N methods, split above N (default: 5)
    "inline_methods": 5,
    # Logo configuration
    # str: path to a single logo file (used for all contexts)
    # dict: {"light": "...", "dark": "...", "alt": "...", "height": "...", "href": "...", "show_title": False}
    # None: auto-detect from conventional paths, or skip if nothing found
    "logo": None,
    # Favicon configuration
    # str: path to a single favicon file
    # dict: {"icon": "...", "apple_touch": "...", "og_image": "..."}
    # None: auto-generate from logo, or skip if no logo
    "favicon": None,
    # Hero section configuration for the landing page
    # None: auto-enable when a logo is configured
    # True/False: force enable/disable
    # dict: {"enabled": bool, "logo": str|dict|false, "logo_height": str,
    #        "name": str|false, "tagline": str|false, "badges": "auto"|list|false}
    "hero": None,
    # Markdown pages (.md generation + copy-page widget)
    # True (default): generate .md pages and show the copy/view widget.
    # False: disable both.
    # Dict form: {"widget": False} generates .md pages but hides the widget.
    "markdown_pages": True,
    # Announcement banner (site-wide banner above the navbar)
    # None/False: no banner (default)
    # str: banner message text (plain text or inline HTML)
    # dict: {"content": str, "type": "info"|"warning"|"success"|"danger",
    #        "dismissable": bool, "url": str|None}
    "announcement": None,
    # Multi-version documentation
    # None/[]: disabled (default — single-version site)
    # list[str | dict]: ordered list of versions (newest first)
    # Minimal: ["0.3", "0.2", "0.1"]
    # Full: [{"tag": "0.3", "label": "0.3.0", "latest": true}, ...]
    "versions": [],
    # Version selector widget configuration
    "version_selector": {
        "enabled": True,  # Enabled automatically when versions is non-empty
        "placement": "navbar-right",  # "navbar-right" | "navbar-left" | "sidebar-top"
        "show_eol": True,  # Include end-of-life versions in dropdown
        "warning_banner": True,  # Show banner on non-latest versions
    },
    # Floating version aliases (/v/latest/, /v/stable/, /v/dev/)
    "version_aliases": {
        "latest": True,  # /v/latest/ -> latest stable version
        "stable": True,  # /v/stable/ -> same as latest
        "dev": True,  # /v/dev/ -> prerelease version (if any)
    },
    # Site-wide accent color (CSS color: hex, named, etc.)
    # Sets the --gd-accent custom property used by shortcodes (hr, etc.),
    # gradient presets, and other accent-colored elements.
    # str: same color for both light and dark mode
    # dict: {"light": str, "dark": str} for per-mode colors
    "accent_color": None,
    # Navbar gradient preset (e.g., "sky", "peach", "lilac", etc.)
    "navbar_style": None,
    # Navbar solid background color (CSS color: hex, named, etc.)
    # str: same color for both light and dark mode
    # dict: {"light": str, "dark": str} for per-mode colors
    # Text color is automatically chosen (light or dark) for contrast using APCA.
    # Overridden when navbar_style (gradient) is set.
    "navbar_color": None,
    # Content area gradient preset (same preset names as navbar_style)
    # Adds a subtle radial glow at the top of the main content area
    # str: preset name (applies to all pages)
    # dict: {"preset": str, "pages": "all"|"homepage"}
    "content_style": None,
    # Scale-to-fit: auto-shrink wide HTML output to fit the content container.
    # Targets elements by CSS selector — the matched element's nearest output
    # wrapper is scaled down (never up) to fit the page width.
    # None/False: disabled (default)
    # list[str]: CSS selectors for elements to auto-scale (e.g., ["#pb_tbl"])
    # Per-page override via frontmatter: `scale-to-fit: ["#pb_tbl"]`
    "scale_to_fit": None,
    # Minimum scale threshold for scale-to-fit.  When scaling would shrink
    # content beyond this limit the element is shown at full size with
    # horizontal scrolling instead.
    # None/False: no minimum (scale as small as needed)
    # float (0-1): minimum scale factor, e.g. 0.4 = "don't shrink below 40%"
    # str keyword: viewport breakpoint below which scaling is disabled:
    #   "mobile"  → scroll on viewports ≤ 576px
    #   "tablet"  → scroll on viewports ≤ 768px
    #   "desktop" → scroll on viewports ≤ 992px
    # Per-page override via frontmatter: `scale-to-fit-min-scale: "tablet"`
    "scale_to_fit_min_scale": None,
    # Navigation icons (Lucide icon set)
    # Prepend icons to sidebar and navbar navigation entries.
    # None/False: disabled (default)
    # dict: {"navbar": {"Label": "icon-name"}, "sidebar": {"Label": "icon-name"}}
    "nav_icons": None,
    # Keyboard navigation & shortcuts
    # True (default): enable keyboard shortcuts and help overlay
    # False: disable keyboard navigation
    "keyboard_nav": True,
    # Package info page (auto-generated page with dependency details)
    # True (default): generate package-info.qmd and link from homepage Meta
    # False: disable package info page generation
    "package_info_page": True,
    # Back-to-top floating button
    # True (default): show back-to-top button on all pages
    # False: disable back-to-top button
    "back_to_top": True,
    # Attribution text in the footer ("Site created with Great Docs")
    # True (default): show attribution
    # False: hide attribution
    "attribution": True,
    # Custom HTML to include in the <head> of every page
    # str: inline HTML text (e.g., a <script> or <link> tag)
    # list[str | dict]: list of inline text strings or {"text": ...} / {"file": ...} entries
    "include_in_header": [],
    # Freeze configuration for Quarto code execution caching
    # Controls whether computational documents are re-executed during builds.
    # None/False: disabled — all documents are executed on every build
    # "auto": re-render only when source changes (execute: freeze: auto) [default]
    # True: never re-render during project render (execute: freeze: true)
    # dict: {"mode": "auto"|true, "pre_render": str|list[str]}
    #   mode: freeze mode ("auto" or true)
    #   pre_render: script(s) to run before Quarto render (e.g., to copy _freeze/ into build dir)
    "freeze": "auto",
    # Pre-render scripts (alternative to freeze.pre_render)
    # Scripts run before Quarto's render step (Quarto's native pre-render hook).
    # str: single script path (relative to project root)
    # list[str]: multiple script paths
    # These are copied into the build directory and configured in _quarto.yml.
    "pre_render": None,
    # Agent Skills (skill.md) generation
    # Generates a SKILL.md file conforming to the Agent Skills specification
    # (https://agentskills.io/) so coding agents can learn to use the package.
    "skill": {
        "enabled": True,
        "file": None,  # Path to a hand-written SKILL.md (overrides auto-generation)
        "well_known": True,  # Also serve at /.well-known/agent-skills/{name}/SKILL.md + index.json
        "gotchas": [],  # List of gotcha strings for the Gotchas section
        "best_practices": [],  # List of best-practice strings
        "decision_table": [],  # Manual rows: [{"need": "...", "use": "..."}]
        "extra_body": None,  # Path to extra Markdown to append to the generated body
        # Multiple named skills (overrides 'file' when set):
        # skills:
        #   - name: my-package
        #     file: skills/my-package/SKILL.md
        #   - name: authoring-pages
        #     file: skills/authoring-pages/SKILL.md
        "skills": [],
    },
    # Social Cards & Open Graph
    # Auto-generate <meta> tags for social media previews (LinkedIn, Discord, Slack,
    # Bluesky, Mastodon, X/Twitter, etc.)
    # True: enable with defaults
    # False/None: disable
    # dict: fine-grained control
    "social_cards": {
        "enabled": True,  # Master switch for social card meta tags
        # Default image for og:image / twitter:image (path relative to project root)
        # None: no default image (individual pages can still set via frontmatter)
        "image": None,
        # Twitter/X card type: "summary", "summary_large_image"
        # "summary_large_image" is used when an image is provided, "summary" otherwise
        "twitter_card": None,  # None = auto-detect based on image
        # Twitter/X @handle for the site (e.g., "@posaboron")
        "twitter_site": None,
    },
    # Page Status Badges
    # Visual indicators for page lifecycle status in sidebar navigation.
    # Pages set `status: new` (or `deprecated`, etc.) in frontmatter.
    # True: enable with defaults
    # False: disable
    # dict: fine-grained control
    "page_status": {
        "enabled": False,  # Master switch for page status badges
        # Show status badges next to sidebar navigation links
        "show_in_sidebar": True,
        # Show status indicator below page titles (like tags)
        "show_on_pages": True,
        # Built-in status definitions (can be extended/overridden)
        # Each status: {label, icon, color, description}
        "statuses": {
            "new": {
                "label": "New",
                "icon": "sparkles",
                "color": "#10b981",  # Emerald green
                "description": "Recently added",
            },
            "updated": {
                "label": "Updated",
                "icon": "refresh-cw",
                "color": "#3b82f6",  # Blue
                "description": "Recently updated",
            },
            "beta": {
                "label": "Beta",
                "icon": "flask-conical",
                "color": "#f59e0b",  # Amber
                "description": "Beta feature",
            },
            "deprecated": {
                "label": "Deprecated",
                "icon": "triangle-alert",
                "color": "#ef4444",  # Red
                "description": "May be removed in a future release",
            },
            "experimental": {
                "label": "Experimental",
                "icon": "beaker",
                "color": "#8b5cf6",  # Purple
                "description": "API may change without notice",
            },
            "upcoming": {
                "label": "Upcoming",
                "icon": "rocket",
                "color": "#e63946",  # Red (Christopher Doyle palette)
                "description": "Coming in a future release",
            },
        },
    },
    # Page Tags
    # Categorize pages with tags for improved discoverability.
    # Tags are added via frontmatter (`tags: [Python, Testing, API]`).
    # True: enable with defaults
    # False: disable
    # dict: fine-grained control
    "tags": {
        "enabled": False,  # Master switch for page tags
        # Auto-generate a tags index page listing all tags and linked pages
        "index_page": True,
        # Render tag pills above page titles with links to the tag index
        "show_on_pages": True,
        # Support hierarchical tags with "/" separator (e.g., "Python/Testing")
        "hierarchical": True,
        # Optional tag icons: dict mapping tag names to Lucide icon names
        # e.g., {"Python": "code", "Tutorial": "book-open"}
        "icons": {},
        # Shadow tags: list of tag names hidden from public view (for internal
        # organization only). Shadow-tagged pages are indexed but tags are not
        # rendered on the page or shown in the tag index.
        "shadow": [],
        # Scoped listings: when True, section pages (user guide, recipes, etc.)
        # show a tag cloud scoped to that section
        "scoped": False,
    },
    # SEO configuration for search engine optimization
    # Generates sitemap.xml, robots.txt, and adds metadata for better discoverability
    "seo": {
        "enabled": True,  # Master switch for all SEO features
        # Sitemap configuration
        "sitemap": {
            "enabled": True,  # Generate sitemap.xml
            "changefreq": {
                # Change frequencies by page type (always|hourly|daily|weekly|monthly|yearly|never)
                "homepage": "weekly",
                "reference": "monthly",
                "user_guide": "monthly",
                "changelog": "weekly",
                "default": "monthly",
            },
            "priority": {
                # Priority values by page type (0.0 to 1.0)
                "homepage": 1.0,
                "reference": 0.8,
                "user_guide": 0.9,
                "changelog": 0.6,
                "default": 0.5,
            },
        },
        # Robots.txt configuration
        "robots": {
            "enabled": True,  # Generate robots.txt
            "allow_all": True,  # Allow all crawlers by default
            "disallow": [],  # List of paths to disallow (e.g., ["/drafts/", "/_internal/"])
            "crawl_delay": None,  # Optional crawl delay in seconds
            "extra_rules": [],  # Additional rules as strings (e.g., ["User-agent: GPTBot", "Disallow: /"])
        },
        # Canonical URL configuration
        "canonical": {
            "enabled": True,  # Add canonical URLs to pages
            "base_url": None,  # Base URL (e.g., "https://example.github.io/pkg/")
            # Auto-detected from GitHub Pages URL if not provided
        },
        # Page title template
        # Supports {page_title} and {site_name} placeholders
        "title_template": "{page_title} | {site_name}",
        # JSON-LD structured data for software documentation
        "structured_data": {
            "enabled": True,  # Add JSON-LD to pages
            "type": "SoftwareSourceCode",  # Schema.org type
            # Additional fields auto-populated from package metadata
        },
        # Default meta description (used when page has no description)
        "default_description": None,  # Falls back to package description
    },
}
