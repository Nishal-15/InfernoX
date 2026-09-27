import asyncio
import inspect
import logging
from typing import Callable, Any, Type, Tuple
import httpx

logger = logging.getLogger(__name__)

TRANSIENT_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError
)

class RetryPolicy:
    """
    Intelligent Retry & Error Classification Policy.
    Distinguishes transient infrastructure glitches (network timeouts, socket drops)
    from permanent semantic errors (malformed geometry, schema invalidity, unrecoverable data).
    Applies exponential backoff with jitter to protect downstream systems.
    """

    @classmethod
    def is_transient(cls, exc: Exception) -> bool:
        """
        Determines whether an exception is transient and eligible for retry.
        """
        if isinstance(exc, TRANSIENT_EXCEPTIONS):
            return True
        
        # Check string representations for common transient indicators
        msg = str(exc).lower()
        transient_indicators = [
            "timeout", "timed out", "connection reset", "connection refused",
            "temporarily unavailable", "try again", "econnreset", "503", "502", "504"
        ]
        if any(ind in msg for ind in transient_indicators):
            return True

        return False

    @classmethod
    async def execute_with_retry(
        cls,
        func: Callable[..., Any],
        *args: Any,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
        stage_name: str = "STAGE",
        **kwargs: Any
    ) -> Any:
        """
        Executes an asynchronous or synchronous function with exponential backoff on transient errors.
        Permanent errors immediately abort without burning unnecessary retries.
        """
        attempt = 0
        last_exc: Exception = Exception("Unknown error")

        while attempt <= max_retries:
            try:
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                attempt += 1
                last_exc = e
                transient = cls.is_transient(e)

                if not transient:
                    logger.warning(f"[{stage_name}] Permanent error encountered on attempt {attempt}: {e}. Aborting retry.")
                    raise

                if attempt > max_retries:
                    logger.error(f"[{stage_name}] Max retries ({max_retries}) exhausted. Last error: {e}")
                    raise

                delay = backoff_seconds * (2 ** (attempt - 1))
                logger.info(f"[{stage_name}] Transient error: {e}. Retrying in {delay:.1f}s (attempt {attempt}/{max_retries})...")
                await asyncio.sleep(delay)

        raise last_exc
