"""Process-local bounded budgets and body limits before authentication/DB work."""
import math
import threading
import time

from starlette.responses import JSONResponse
from src.core.config import get_api_security_settings

PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"}


class FixedWindowLimiter:
    def __init__(self, max_buckets=10_000, clock=time.monotonic):
        self.max_buckets = max_buckets
        self.clock = clock
        self.buckets = {}
        self.lock = threading.Lock()

    def check(self, key, limit, window):
        now = self.clock()
        with self.lock:
            expired = [key for key, (_, until) in self.buckets.items() if until <= now]
            for item in expired:
                del self.buckets[item]
            count, until = self.buckets.get(key, (0, now + window))
            if key not in self.buckets and len(self.buckets) >= self.max_buckets:
                return max(1, math.ceil(window))
            if count >= limit:
                return max(1, math.ceil(until - now))
            self.buckets[key] = (count + 1, until)
            return 0


class ApiSecurityMiddleware:
    def __init__(self, app, settings=None, limiter=None):
        self.app = app
        self.settings = settings or get_api_security_settings()
        self.limiter = limiter or FixedWindowLimiter(self.settings.rate_max_buckets)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def private_send(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() not in {b"cache-control", b"x-content-type-options"}]
                headers.extend((k.lower().encode(), v.encode()) for k, v in PRIVATE_HEADERS.items())
                message = {**message, "headers": headers}
            await send(message)

        async def reject(status, retry=None):
            headers = {"Retry-After": str(retry)} if retry else {}
            response = JSONResponse({"message": "Request rejected"}, status_code=status, headers=headers)
            await response(scope, receive, private_send)

        path = scope.get("path", "")
        auth = path.startswith("/auth/candidate/") and scope.get("method") == "POST"
        lookup = path in {"/ho-so/tra-cuu", "/ho-so/ket-qua/tra-cuu"}
        if auth or lookup:
            # ASGI peer only. Never accept X-Forwarded-For/X-Real-IP from clients.
            peer = (scope.get("client") or ("unknown",))[0]
            retry = self.limiter.check(("auth" if auth else "lookup", peer),
                self.settings.auth_rate_limit if auth else self.settings.lookup_rate_limit,
                self.settings.rate_window_seconds)
            if retry:
                return await reject(429, retry)

        if scope.get("method") in {"POST", "PUT", "PATCH", "DELETE"}:
            headers = dict(scope.get("headers", []))
            maximum = self.settings.auth_max_bytes if auth else self.settings.json_max_bytes
            length = headers.get(b"content-length")
            if length is not None and (not length.isdigit() or int(length) > maximum):
                return await reject(413)
            chunks, size = [], 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > maximum:
                    return await reject(413)
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break
            body = b"".join(chunks)
            consumed = False

            async def replay():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            return await self.app(scope, replay, private_send)
        await self.app(scope, receive, private_send)
