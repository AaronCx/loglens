# loglens-sdk

Python SDK for the [LogLens](https://github.com/AaronCx/loglens) error monitoring platform.

## Installation

```bash
pip install loglens-sdk
```

Or from source:

```bash
pip install ./sdk
```

## Quick Start

```python
from loglens_sdk import LogLens

ll = LogLens(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    service="my-service",
    environment="production",
)

# Basic capture
ll.capture("Something went wrong", severity="error")

# Severity shortcuts
ll.info("User logged in", metadata={"user_id": 42})
ll.warning("Cache miss rate high", metadata={"rate": 0.87})
ll.error("Payment failed", metadata={"order_id": "ord_123"})
ll.critical("Database unreachable!")

# Capture current exception automatically
try:
    1 / 0
except ZeroDivisionError:
    ll.capture_exception()
```

## Global Singleton

```python
import loglens_sdk

loglens_sdk.init(
    api_url="http://localhost:8000",
    api_key="your-api-key",
    service="my-api",
)

# Anywhere in your code:
loglens_sdk.capture("Request failed", severity="error")
```

## API Reference

### `LogLens(api_url, api_key, service, environment, timeout, async_send)`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | str | `$LOGLENS_API_URL` | Backend URL |
| `api_key` | str | `$LOGLENS_API_KEY` | API key |
| `service` | str | `"default"` | Default service name |
| `environment` | str | `"production"` | Default environment |
| `timeout` | float | `5.0` | Request timeout (s) |
| `async_send` | bool | `True` | Send in background thread |

### `capture(message, severity, service, stack_trace, metadata, environment, exc_info)`

Send a log event. Returns the created event dict when `async_send=False`, otherwise `None`.

### `capture_exception(exc, service, severity, metadata)`

Capture an exception with its full traceback. Pass `exc=None` to use the current `sys.exc_info()`.
