import asyncio
import time


class AsyncRateLimiter:
    def __init__(self, rpm):
        self.rpm = max(1, int(rpm))
        self.interval = 60.0 / self.rpm + 0.1
        self.lock = asyncio.Lock()
        self.last_call = 0.0

    async def wait(self):
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call

            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)

            self.last_call = time.time()