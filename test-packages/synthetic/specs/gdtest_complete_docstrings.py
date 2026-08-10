"""
gdtest_complete_docstrings — Rich docstrings for non-class/function objects.

Dimensions: A1, B1, C12, D1, E3, F6, G1, H7
Focus: comprehensive docstrings (summary + extended description + sections) on
       objects that typically receive little documentation: constants, module-level
       variables, type aliases, TypeVar/ParamSpec, properties, and the module itself.
       Complements gdtest_constants (minimal docstrings) and gdtest_type_aliases
       (PEP 695 focus) by exercising the full docstring machinery on these kinds.
"""

SPEC = {
    "name": "gdtest_complete_docstrings",
    "description": "Complete docstrings for constants, variables, type aliases, TypeVars, properties, and modules",
    "dimensions": ["A1", "B1", "C12", "D1", "E3", "F6", "G1", "H7"],
    "pyproject_toml": {
        "project": {
            "name": "gdtest-complete-docstrings",
            "version": "0.1.0",
            "description": (
                "A synthetic test package demonstrating complete docstrings "
                "for objects beyond functions and classes"
            ),
        },
        "build-system": {
            "requires": ["setuptools"],
            "build-backend": "setuptools.build_meta",
        },
    },
    "files": {
        "gdtest_complete_docstrings/__init__.py": '''\
            """Connection pooling and lifecycle management.

            This module owns the connection pool, the health-check loop, and
            the retry logic that wraps individual queries. Most users interact
            with it through `get_connection()` and the `Connection` context
            manager; the pool configuration constants are exposed for tuning.

            Notes
            -----
            The pool is process-global. Forking after the pool has been
            initialized leads to shared file descriptors; use
            `reinitialize()` in the child process.

            %seealso Connection, get_connection
            """

            __version__ = "0.1.0"
            __all__ = [
                "MAX_CONNECTIONS",
                "MIN_CONNECTIONS",
                "SUPPORTED_BACKENDS",
                "timeout",
                "retry_delay",
                "ConnectionId",
                "BackendName",
                "PoolKey",
                "Sortable",
                "Handler",
                "Connection",
                "get_connection",
                "reinitialize",
            ]

            from typing import Final, TypeAlias, TypeVar, Callable, Literal


            # ── Constants ────────────────────────────────────────────────

            MAX_CONNECTIONS: Final[int] = 128
            """Upper bound on simultaneous database connections.

            Exceeding this limit raises `ConnectionPoolExhausted`. The
            default of 128 matches the PostgreSQL `max_connections` default
            so that a single application instance can saturate one server
            without over-provisioning.

            Notes
            -----
            Deployments behind a connection pooler (PgBouncer, Odyssey) can
            safely raise this to 500 or more, since the pooler manages the
            actual backend connection count.

            %seealso MIN_CONNECTIONS, Connection
            """

            MIN_CONNECTIONS: Final[int] = 4
            """Lower bound on warm connections kept in the pool.

            The pool always keeps at least this many connections open, even
            during idle periods. This avoids the latency spike that comes
            from establishing a fresh connection on the first request after
            an idle window.

            Notes
            -----
            Set this to 0 in test environments where connection setup is
            expensive and the pool is never actually used.

            %seealso MAX_CONNECTIONS
            """

            SUPPORTED_BACKENDS: Final[tuple[str, ...]] = (
                "postgresql",
                "mysql",
                "sqlite",
            )
            """Database backends the pool can connect to.

            Each backend name must match a registered driver in the driver
            registry. Adding a new backend requires implementing the
            `Driver` protocol and registering it before pool initialization.

            Examples
            --------
            Check whether a backend is available before connecting:

            ```python
            if "postgresql" in SUPPORTED_BACKENDS:
                conn = get_connection("postgresql")
            ```

            %seealso get_connection, BackendName
            """


            # ── Module-level variables ───────────────────────────────────

            timeout: int = 30
            """Seconds to wait before abandoning a connection attempt.

            Set this before calling any connection functions. Values below 1
            are treated as "no timeout" (the attempt blocks indefinitely).
            The default of 30 seconds suits most interactive use; batch
            pipelines may want 120 or more.

            Examples
            --------
            ```python
            import gdtest_complete_docstrings as pool

            pool.timeout = 60  # generous timeout for batch jobs
            ```

            %seealso retry_delay, get_connection
            """

            retry_delay: float = 1.5
            """Seconds to wait between retry attempts after a failed connect.

            An exponential backoff multiplier is applied on each subsequent
            retry, so the actual delay doubles each time: 1.5, 3.0, 6.0,
            and so on. Set to 0 to disable the delay entirely (useful in
            tests).

            Notes
            -----
            The maximum effective delay is capped at `timeout`; if the
            cumulative delay would exceed the timeout, the pool gives up
            immediately instead of sleeping.

            %seealso timeout
            """


            # ── Type aliases ─────────────────────────────────────────────

            ConnectionId: TypeAlias = str
            """An opaque handle for a single pooled connection.

            Connection IDs are generated by the pool and are unique within
            the lifetime of the process. They appear in log messages and
            health-check output, so they are strings rather than integers
            for readability.

            %seealso Connection, get_connection
            """

            BackendName: TypeAlias = Literal[
                "postgresql", "mysql", "sqlite"
            ]
            """A supported database backend, as a string literal.

            Using a `Literal` type rather than a plain `str` lets type
            checkers catch misspelled backend names at analysis time instead
            of at runtime.

            %seealso SUPPORTED_BACKENDS, get_connection
            """

            PoolKey: TypeAlias = tuple[BackendName, str, int]
            """A unique identifier for a connection pool instance.

            The triple `(backend, host, port)` distinguishes pools that
            target different servers. Two calls to `get_connection()` with
            the same pool key reuse the same underlying pool.

            %seealso BackendName, get_connection
            """


            # ── TypeVar ──────────────────────────────────────────────────

            Sortable = TypeVar("Sortable", bound="Connection")
            """A connection type that can be compared for priority ordering.

            Any type substituted for `Sortable` must be a `Connection`
            subclass. This is used internally by the priority queue that
            schedules health checks: connections with the oldest last-used
            timestamp are checked first.

            Notes
            -----
            The bound is `Connection` rather than a protocol because the
            priority comparison depends on internal state (`_last_used`)
            that is not part of any public protocol.

            %seealso Connection
            """

            Handler = TypeVar("Handler", bound=Callable)
            """A callable that handles connection lifecycle events.

            Handlers are registered with `Connection.on_close()` and
            `Connection.on_error()`. The `Callable` bound ensures that
            only callables can be registered, while leaving the signature
            flexible enough for both synchronous and asynchronous handlers.

            %seealso Connection
            """


            # ── Class with properties ────────────────────────────────────

            class Connection:
                """A managed database connection drawn from the pool.

                Connections track their own state (idle, active, closed) and
                expose that state through read-only properties. Use
                `get_connection()` to obtain one; call `close()` when
                finished.

                Parameters
                ----------
                backend
                    Which database backend this connection targets.
                connection_id
                    The pool-assigned unique identifier.

                %seealso get_connection, reinitialize
                """

                def __init__(
                    self,
                    backend: BackendName,
                    connection_id: ConnectionId,
                ) -> None:
                    self._backend = backend
                    self._id = connection_id
                    self._in_flight: int = 0
                    self._closed: bool = False

                @property
                def is_idle(self) -> bool:
                    """Whether the connection has no in-flight queries.

                    Computed from the internal transaction counter, so this
                    is always consistent even if queries are being submitted
                    from another thread. An idle connection can be safely
                    returned to the pool or closed.

                    Returns
                    -------
                    bool
                        `True` when no queries are running on this
                        connection.

                    %seealso is_closed, close
                    """
                    return self._in_flight == 0

                @property
                def is_closed(self) -> bool:
                    """Whether the connection has been permanently closed.

                    A closed connection cannot be reused. Attempting to
                    execute a query on a closed connection raises
                    `ConnectionClosedError`.

                    Returns
                    -------
                    bool
                        `True` after `close()` has been called.

                    %seealso is_idle, close
                    """
                    return self._closed

                @property
                def backend(self) -> BackendName:
                    """The database backend this connection targets.

                    This is the backend name passed at construction time and
                    does not change over the connection's lifetime. Useful
                    for dispatching backend-specific SQL dialect adjustments.

                    Returns
                    -------
                    BackendName
                        One of the `SUPPORTED_BACKENDS` values.

                    %seealso SUPPORTED_BACKENDS, BackendName
                    """
                    return self._backend

                @property
                def connection_id(self) -> ConnectionId:
                    """The pool-assigned unique identifier for this connection.

                    Appears in log output and health-check reports. Two
                    connections never share an ID within the same process,
                    even after one has been closed and garbage-collected.

                    Returns
                    -------
                    ConnectionId
                        A human-readable string identifier.

                    %seealso ConnectionId
                    """
                    return self._id

                def close(self) -> None:
                    """Close the connection and return it to the pool.

                    After calling `close()`, `is_closed` returns `True` and
                    any further operations on this connection raise
                    `ConnectionClosedError`.

                    %seealso is_closed, is_idle
                    """
                    self._closed = True


            # ── Functions ────────────────────────────────────────────────

            def get_connection(
                backend: BackendName = "postgresql",
                host: str = "localhost",
                port: int = 5432,
            ) -> Connection:
                """Obtain a connection from the pool.

                If a pool for the given `(backend, host, port)` triple already
                exists, a connection is drawn from it. Otherwise a new pool is
                created with `MIN_CONNECTIONS` warm connections.

                Parameters
                ----------
                backend
                    Which database backend to connect to.
                host
                    The server hostname or IP address.
                port
                    The server port number.

                Returns
                -------
                Connection
                    A ready-to-use connection.

                Raises
                ------
                ConnectionPoolExhausted
                    If the pool has reached `MAX_CONNECTIONS`.
                TimeoutError
                    If a connection cannot be established within `timeout`
                    seconds.

                %seealso Connection, MAX_CONNECTIONS, timeout
                """
                return Connection(backend, f"{host}:{port}:0")


            def reinitialize() -> None:
                """Reset the global connection pool.

                Call this after `os.fork()` to avoid sharing file
                descriptors between parent and child processes. All existing
                connections are closed and new ones are established.

                Notes
                -----
                This is a no-op if the pool has not been initialized yet.

                %seealso get_connection, MIN_CONNECTIONS
                """
                pass
        ''',
        "README.md": """\
            # gdtest-complete-docstrings

            A synthetic test package demonstrating complete docstrings for
            objects that typically receive minimal documentation: constants,
            module-level variables, type aliases, TypeVars, and properties.
        """,
    },
    "expected": {
        "detected_name": "gdtest-complete-docstrings",
        "detected_module": "gdtest_complete_docstrings",
        "detected_parser": "numpy",
        "export_names": [
            "BackendName",
            "Connection",
            "ConnectionId",
            "Handler",
            "MAX_CONNECTIONS",
            "MIN_CONNECTIONS",
            "PoolKey",
            "SUPPORTED_BACKENDS",
            "Sortable",
            "get_connection",
            "reinitialize",
            "retry_delay",
            "timeout",
        ],
        "num_exports": 13,
        "section_titles": ["Classes", "Functions", "Constants"],
        "has_user_guide": False,
        "coverage_exclude": ["nodoc", "bigcl", "ug", "supp", "sechdg", "sbsec", "hdg"],
    },
}
