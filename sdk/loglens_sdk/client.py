"""
LogLens Python SDK
==================
A lightweight SDK for sending error events to a LogLens backend.

Usage
-----
    from loglens_sdk import LogLens

    ll = LogLens(api_url="http://localhost:8000", api_key="your-key")
    ll.capture("Something went wrong", severity="error", service="my-service")

    # Or use the global singleton after configuring it:
    import loglens_sdk
    loglens_sdk.init(api_url="...", api_key="...")
    loglens_sdk.capture("Oops", severity="critical", service="auth")
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
import threading
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import requests

logger = logging.getLogger("loglens")

Severity = Literal["info", "warning", "error", "critical"]

_global_client: Optional["LogLens"] = None


def init(
    api_url: Optional[str] = None,
    api_key: Optional[str] = None,
    service: str = "default",
    environment: str = "production",
    timeout: float = 5.0,
) -> "LogLens":
    """Configure and return the global LogLens client."""
    global _global_client
    _global_client = LogLens(
        api_url=api_url,
        api_key=api_key,
        service=service,
        environment=environment,
        timeout=timeout,
    )
    return _global_client


def capture(
    message: str,
    severity: Severity = "error",
    service: Optional[str] = None,
    stack_trace: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    environment: Optional[str] = None,
    exc_info: bool = False,
) -> Optional[dict]:
    """Send an event using the global client (call init() first)."""
    if _global_client is None:
        raise RuntimeError(
            "LogLens is not initialized. Call loglens_sdk.init(api_url=..., api_key=...) first."
        )
    return _global_client.capture(
        message=message,
        severity=severity,
        service=service,
        stack_trace=stack_trace,
        metadata=metadata,
        environment=environment,
        exc_info=exc_info,
    )


class LogLens:
    """
    Client for the LogLens error-logging API.

    Parameters
    ----------
    api_url : str
        Base URL of the LogLens backend, e.g. ``http://localhost:8000``.
        Falls back to the ``LOGLENS_API_URL`` environment variable.
    api_key : str
        API key for authentication.
        Falls back to the ``LOGLENS_API_KEY`` environment variable.
    service : str
        Default service name included with every event.
    environment : str
        Default environment tag (e.g. "production", "staging").
    timeout : float
        Request timeout in seconds (default 5).
    async_send : bool
        If True (default), events are sent in a background thread so your
        application is never blocked.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        service: str = "default",
        environment: str = "production",
        timeout: float = 5.0,
        async_send: bool = True,
    ) -> None:
        self.api_url = (api_url or os.getenv("LOGLENS_API_URL", "http://localhost:8000")).rstrip("/")
        self.api_key = api_key or os.getenv("LOGLENS_API_KEY", "")
        self.service = service
        self.environment = environment
        self.timeout = timeout
        self.async_send = async_send
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.api_key, "Content-Type": "application/json"})

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture(
        self,
        message: str,
        severity: Severity = "error",
        service: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        environment: Optional[str] = None,
        exc_info: bool = False,
    ) -> Optional[dict]:
        """
        Send a log event to the LogLens backend.

        Parameters
        ----------
        message : str
            Human-readable description of the event.
        severity : "info" | "warning" | "error" | "critical"
            Event severity level.
        service : str, optional
            Override the default service name.
        stack_trace : str, optional
            Explicit stack trace string. If *exc_info* is True and this is
            omitted the current exception traceback is used automatically.
        metadata : dict, optional
            Arbitrary key/value data to attach to the event.
        environment : str, optional
            Override the default environment tag.
        exc_info : bool
            If True, capture the current exception's traceback automatically.

        Returns
        -------
        dict or None
            The created event object returned by the API, or None if
            *async_send* is True (fire-and-forget).
        """
        if exc_info and stack_trace is None:
            exc = sys.exc_info()
            if exc[0] is not None:
                stack_trace = "".join(traceback.format_exception(*exc))

        payload = {
            "severity": severity,
            "service": service or self.service,
            "message": message,
            "stack_trace": stack_trace,
            "metadata": metadata or {},
            "environment": environment or self.environment,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if self.async_send:
            t = threading.Thread(target=self._send, args=(payload,), daemon=True)
            t.start()
            return None

        return self._send(payload)

    def info(self, message: str, **kwargs) -> Optional[dict]:
        """Shortcut for ``capture(..., severity='info')``."""
        return self.capture(message, severity="info", **kwargs)

    def warning(self, message: str, **kwargs) -> Optional[dict]:
        """Shortcut for ``capture(..., severity='warning')``."""
        return self.capture(message, severity="warning", **kwargs)

    def error(self, message: str, **kwargs) -> Optional[dict]:
        """Shortcut for ``capture(..., severity='error')``."""
        return self.capture(message, severity="error", **kwargs)

    def critical(self, message: str, **kwargs) -> Optional[dict]:
        """Shortcut for ``capture(..., severity='critical')``."""
        return self.capture(message, severity="critical", **kwargs)

    def capture_exception(
        self,
        exc: Optional[BaseException] = None,
        service: Optional[str] = None,
        severity: Severity = "error",
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[dict]:
        """
        Capture an exception, automatically formatting its traceback.

        Parameters
        ----------
        exc : BaseException, optional
            The exception to capture. If omitted, the current exception
            from ``sys.exc_info()`` is used.
        """
        if exc is not None:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            message = f"{type(exc).__name__}: {exc}"
        else:
            exc_tuple = sys.exc_info()
            if exc_tuple[0] is None:
                raise ValueError("No active exception to capture.")
            tb = "".join(traceback.format_exception(*exc_tuple))
            message = f"{exc_tuple[0].__name__}: {exc_tuple[1]}"

        return self.capture(
            message=message,
            severity=severity,
            service=service,
            stack_trace=tb,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _send(self, payload: dict) -> Optional[dict]:
        try:
            resp = self._session.post(
                f"{self.api_url}/events",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            logger.warning("LogLens: failed to send event: %s", exc)
            return None

    def __repr__(self) -> str:
        return f"LogLens(api_url={self.api_url!r}, service={self.service!r})"
