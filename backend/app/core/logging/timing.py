import time
import logging
from contextlib import contextmanager
from typing import Generator, Any, Dict, Optional, Tuple, Callable

logger = logging.getLogger(__name__)


@contextmanager
def timed_operation(
    log: logging.Logger,
    event_name: str,
    extra: Optional[Dict[str, Any]] = None,
    log_level: int = logging.INFO,
) -> Generator[Dict[str, Any], None, None]:
    """
    Context manager to time operational blocks and emit structured latency metrics.
    Emits an error log if the block raises an unhandled exception.
    """
    start_time = time.perf_counter()
    metrics: Dict[str, Any] = {"event": event_name}
    if extra:
        metrics.update(extra)

    try:
        yield metrics
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        metrics["duration_ms"] = duration_ms
        log.log(
            log_level,
            f"Operation '{event_name}' completed in {duration_ms}ms",
            extra=metrics,
        )
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        metrics["duration_ms"] = duration_ms
        metrics["error_type"] = type(exc).__name__
        metrics["error_message"] = str(exc)
        log.error(
            f"Operation '{event_name}' failed after {duration_ms}ms: {exc}",
            extra=metrics,
            exc_info=True,
        )
        raise


def measure_latency(func: Callable, *args: Any, **kwargs: Any) -> Tuple[Any, float]:
    """
    Executes a callable and returns a tuple of (result, duration_ms).
    """
    start = time.perf_counter()
    res = func(*args, **kwargs)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    return res, duration_ms
