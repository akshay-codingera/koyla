import time
import logging
from collections import defaultdict, deque
from threading import Lock
from typing import Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Sliding-window rate limiter with Redis backend and thread-safe in-memory fallback.
    Defends authentication, retrieval, and upload endpoints against brute-force
    and resource exhaustion attacks.
    """
    def __init__(self, requests_per_minute: int, scope: str = "default"):
        self.requests_per_minute = requests_per_minute
        self.scope = scope
        self.window_seconds = 60
        self._memory_store = defaultdict(deque)
        self._lock = Lock()
        self._redis_client = None
        self._redis_tested = False

    def _get_redis(self):
        if not self._redis_tested:
            self._redis_tested = True
            try:
                import redis
                r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=0.5)
                if r.ping():
                    self._redis_client = r
            except Exception:
                self._redis_client = None
        return self._redis_client

    def _get_client_id(self, request: Request) -> str:
        # Check X-Forwarded-For header if behind a reverse proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
        elif request.client:
            client_ip = request.client.host
        else:
            client_ip = "127.0.0.1"
        return f"{self.scope}:{client_ip}"

    def check_rate_limit(self, client_id: str) -> Optional[int]:
        """
        Returns retry_after seconds if rate limit exceeded, or None if permitted.
        """
        if not getattr(settings, "RATE_LIMIT_ENABLED", True):
            return None

        # 1. Try Redis sliding window if available
        r = self._get_redis()
        if r is not None:
            try:
                now = time.time()
                key = f"rate_limit:{client_id}"
                pipe = r.pipeline()
                pipe.zremrangebyscore(key, 0, now - self.window_seconds)
                pipe.zcard(key)
                pipe.zadd(key, {str(now): now})
                pipe.expire(key, self.window_seconds + 5)
                _, count, _, _ = pipe.execute()
                
                if count >= self.requests_per_minute:
                    # Remove the timestamp we just added since request is rejected
                    r.zrem(key, str(now))
                    return self.window_seconds
                return None
            except Exception as e:
                logger.warning(f"Redis rate limiter exception ({e}), falling back to memory: {e}")
                self._redis_client = None

        # 2. In-memory sliding window fallback
        now = time.time()
        with self._lock:
            q = self._memory_store[client_id]
            cutoff = now - self.window_seconds
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.requests_per_minute:
                retry_after = max(1, int(self.window_seconds - (now - q[0])))
                return retry_after
            q.append(now)
            return None

    def reset(self):
        """Clears rate limit state for tests."""
        with self._lock:
            self._memory_store.clear()
        r = self._get_redis()
        if r is not None:
            try:
                keys = set(r.keys(f"rate_limit:{self.scope}:*")) | set(r.keys("rate_limit:test*"))
                if keys:
                    r.delete(*keys)
            except Exception:
                pass

    async def __call__(self, request: Request):
        client_id = self._get_client_id(request)
        retry_after = self.check_rate_limit(client_id)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {self.scope}. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
