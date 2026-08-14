import functools
import logging
import time

log = logging.getLogger("flow.retry")


def with_retries(attempts=3, base_delay=0.05, exceptions=(Exception,)):
    """Retry with exponential backoff.

    The whole point of a production workflow versus a demo: a transient
    failure (a model timeout, a flaky API, an expired token being refreshed)
    should not take the run down. Retry the small stuff, surface the rest.
    """
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last = None
            for i in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last = e
                    log.warning("attempt %d/%d for %s failed: %s",
                                i, attempts, fn.__name__, e)
                    if i < attempts:
                        time.sleep(delay)
                        delay *= 2
            raise last
        return wrapper
    return deco
