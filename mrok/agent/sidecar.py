import logging
import select
import signal
import socket
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httptools
import openziti

logger = logging.getLogger(__name__)


class BaseWorker(ABC):
    """Abstract base class for workers."""

    @abstractmethod
    def handle_connection(self, ziti_socket: socket.socket) -> None:
        """Handle a connection from a Ziti client.

        Args:
            ziti_socket: The socket connected to the Ziti client
        """
        pass


class AccessLogger:
    """Base access logger that can be subclassed for custom logging destinations."""

    def log_access(
        self,
        method: str,
        path: str,
        status: int,
        request_size: int,
        response_size: int,
        duration: float,
        client_ip: str = "127.0.0.1",
    ) -> None:
        """Log HTTP access information."""
        logger.info(
            f"{client_ip} - - [{time.strftime('%d/%b/%Y:%H:%M:%S %z')}] "
            f'"{method} {path} HTTP/1.1" {status} {response_size} '
            f'"{request_size}" "{duration:.3f}"'
        )

    def log_error(self, error: Exception, context: str = "") -> None:
        """Log HTTP error information."""
        logger.error(f"HTTP Worker Error {context}: {error}")


class ErrorLogger:
    """Base error logger that can be subclassed for custom error destinations."""

    def log_error(self, error: Exception, context: str = "") -> None:
        """Log error information."""
        logger.error(f"Error {context}: {error}")


class HttpState:
    def __init__(self) -> None:
        self.request_start_time: float | None = None
        self.http_method: str | None = None
        self.http_path: str | None = None
        self.http_status: int | None = None
        self.request_size: int = 0
        self.response_size: int = 0
        self.lock = threading.Lock()


class HttpWorker(BaseWorker):
    """Worker that handles HTTP connections with single thread and httptools parsing."""

    def __init__(
        self,
        target_address: str,
        access_logger: AccessLogger | None = None,
        error_logger: ErrorLogger | None = None,
    ):
        self.target_address = target_address
        self.access_logger = access_logger or AccessLogger()
        self.error_logger = error_logger or ErrorLogger()

    def handle_connection(self, ziti_socket: socket.socket) -> None:
        """Handle HTTP connection with single thread and proper HTTP parsing."""
        target_socket = None
        try:
            # Connect to target
            if ":" in self.target_address:
                # TCP socket: host:port
                host, port = self.target_address.split(":", 1)
                target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                target_socket.connect((host, int(port)))
                logger.info(f"HTTP Worker: Connected to target {self.target_address}")
            else:
                # Unix socket: path
                target_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                target_socket.connect(self.target_address)
                logger.info(f"HTTP Worker: Connected to target Unix socket {self.target_address}")

            # Handle HTTP connection with single thread
            self._handle_http_connection(ziti_socket, target_socket)

        except Exception as e:
            self.error_logger.log_error(e, "connection setup")
        finally:
            # Clean up sockets
            try:
                if target_socket:
                    target_socket.close()
            except (OSError, AttributeError):
                pass
            try:
                ziti_socket.close()
            except (OSError, AttributeError):
                pass

    def _handle_http_connection(
        self, ziti_socket: socket.socket, target_socket: socket.socket
    ) -> None:
        """Handle HTTP connection with httptools parsing in single thread."""
        http_state = HttpState()

        def reset_http_state():
            """Reset HTTP tracking state for next request."""
            http_state.request_start_time = None
            http_state.http_method = None
            http_state.http_path = None
            http_state.http_status = None
            http_state.request_size = 0
            http_state.response_size = 0

        def invoke_callback():
            """Invoke callback if data is available."""
            if (
                http_state.http_method
                and http_state.http_path
                and http_state.http_status is not None
                and http_state.request_start_time
            ):
                time_taken = time.time() - http_state.request_start_time
                try:
                    # Log access
                    self.access_logger.log_access(
                        http_state.http_method,
                        http_state.http_path,
                        http_state.http_status,
                        http_state.request_size,
                        http_state.response_size,
                        time_taken,
                    )
                except Exception as e:
                    self.error_logger.log_error(e, "access logging")
                finally:
                    reset_http_state()

        # Create parser callbacks that have access to http_state
        class ParserCallbacks:
            def __init__(self, http_state):
                self.http_state = http_state

            def on_url(self, url: bytes) -> None:
                """Called when URL is parsed."""
                if not self.http_state.http_path:
                    self.http_state.http_path = url.decode("utf-8", errors="ignore")

            def on_method(self, method: bytes) -> None:
                """Called when HTTP method is parsed."""
                if not self.http_state.http_method:
                    self.http_state.http_method = method.decode("utf-8")
                    self.http_state.request_start_time = time.time()

            def on_status(self, status: bytes) -> None:
                """Called when HTTP status is parsed."""
                if self.http_state.http_status is None:
                    try:
                        self.http_state.http_status = int(status.decode("utf-8"))
                    except ValueError:
                        pass

        # HTTP request and response parsers
        callbacks = ParserCallbacks(http_state)
        request_parser = httptools.HttpRequestParser(callbacks)
        response_parser = httptools.HttpResponseParser(callbacks)

        try:
            # Set socket timeouts
            ziti_socket.settimeout(1.0)
            target_socket.settimeout(1.0)

            while True:
                # Use select to wait for data on either socket
                ready_sockets, _, _ = select.select([ziti_socket, target_socket], [], [], 1.0)

                if not ready_sockets:
                    continue  # Timeout, continue loop

                for sock in ready_sockets:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            # Connection closed
                            invoke_callback()
                            return

                        if sock is ziti_socket:
                            # Data from Ziti client -> target server
                            http_state.request_size += len(data)
                            # Parse HTTP request with httptools
                            request_parser.feed_data(data)
                            target_socket.sendall(data)

                        else:  # sock is target_socket
                            # Data from target server -> Ziti client
                            http_state.response_size += len(data)
                            # Parse HTTP response with httptools
                            response_parser.feed_data(data)
                            ziti_socket.sendall(data)

                    except TimeoutError:
                        continue
                    except Exception as e:
                        self.error_logger.log_error(e, "socket operation")
                        return

        except Exception as e:
            self.error_logger.log_error(e, "connection handling")


class ZitiTunnel:
    def __init__(
        self,
        identity: str,
        service: str,
        worker_class: type[BaseWorker],
        worker_kwargs: dict[str, Any] | None = None,
    ):
        self.identity = identity
        self.service = service
        self.worker_class = worker_class
        self.worker_kwargs = worker_kwargs or {}

        self._shutdown_event = threading.Event()
        self._tunnel_thread = None
        self._thread_pool: ThreadPoolExecutor | None = None
        self._running = False

    def start(self):
        if self._running:
            logger.warning("Tunnel is already running")
            return

        logger.info(f"Starting tunnel: Ziti service '{self.service}'")

        ctx, err = openziti.load(self.identity)
        if err != 0:
            raise RuntimeError(f"Failed to load Ziti identity from {self.identity}: {err}")

        self._ziti_sock = ctx.bind(self.service)
        self._ziti_sock.listen(5)

        logger.info(f"Tunnel listening for Ziti connections on service '{self.service}'")

        # Start the main tunnel thread and thread pool
        self._shutdown_event.clear()
        self._thread_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="tunnel-worker")
        self._tunnel_thread = threading.Thread(target=self._run_tunnel, daemon=True)
        self._tunnel_thread.start()
        self._running = True

    def stop(self, timeout: float = 5.0):
        """Stop the tunnel and wait for all threads to finish."""
        if not self._running:
            logger.warning("Tunnel is not running")
            return

        logger.info("Stopping tunnel...")
        self._shutdown_event.set()

        # Close the Ziti socket first to interrupt any blocking operations
        try:
            if hasattr(self, "_ziti_sock"):
                self._ziti_sock.close()
        except Exception:
            pass

        # Wait for tunnel thread to finish
        if self._tunnel_thread and self._tunnel_thread.is_alive():
            self._tunnel_thread.join(timeout=timeout)

        # Shutdown thread pool
        if self._thread_pool:
            self._thread_pool.shutdown(wait=True)

        self._running = False
        logger.info("Tunnel stopped")

    def _run_tunnel(self):
        """Main tunnel loop that accepts Ziti connections."""
        try:
            while not self._shutdown_event.is_set():
                try:
                    # Accept connection from Ziti client
                    ziti_conn, ziti_addr = self._ziti_sock.accept()
                    logger.info(f"Tunnel: Accepted Ziti connection from {ziti_addr}")

                    # Handle the connection using the provided worker class
                    if self._thread_pool is None:
                        logger.error("Thread pool not initialized")
                        continue
                    worker_instance = self.worker_class(**self.worker_kwargs)
                    self._thread_pool.submit(worker_instance.handle_connection, ziti_conn)

                except TimeoutError:
                    continue
                except Exception as e:
                    if not self._shutdown_event.is_set():
                        logger.exception(f"Tunnel connection error: {e}")
                    break

        except Exception as e:
            logger.error(f"Tunnel error: {e}")

    def is_running(self) -> bool:
        """Check if the tunnel is running."""
        return self._running and not self._shutdown_event.is_set()

    def run(self, signals: tuple[int, ...] = (signal.SIGTERM, signal.SIGINT)) -> None:
        """Start the tunnel and wait for Unix signals to stop.

        Args:
            signals: Tuple of signal numbers to listen for (default: SIGTERM, SIGINT)
        """
        if self._running:
            logger.warning("Tunnel is already running")
            return

        # Set up signal handlers
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, shutting down tunnel...")
            self.stop()

        # Register signal handlers
        for sig in signals:
            signal.signal(sig, signal_handler)

        try:
            # Start the tunnel
            self.start()

            # Wait for shutdown signal
            while self._running:
                try:
                    # Wait for shutdown event or timeout
                    if self._shutdown_event.wait(timeout=1.0):
                        break
                except KeyboardInterrupt:
                    logger.info("Received KeyboardInterrupt, shutting down tunnel...")
                    break

        except Exception as e:
            logger.error(f"Error in tunnel run loop: {e}")
        finally:
            # Ensure tunnel is stopped
            if self._running:
                self.stop()
