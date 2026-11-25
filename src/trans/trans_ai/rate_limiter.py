import asyncio
import time
import random
from . import config


class AsyncRateLimiter:
    def __init__(self, rpm, burst=1):
        self.rpm = max(1, int(rpm))
        self.interval = 60.0 / self.rpm
        self.burst = max(1, int(burst))
        self._burst_remaining = self.burst
        self._lock = None
        self._loop = None
        self.next_call = 0.0

    def _get_lock(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._lock is None or self._loop is not loop:
            self._lock = asyncio.Lock()
            self._loop = loop
            self.next_call = 0.0
            self._burst_remaining = self.burst
        return self._lock

    async def wait(self):
        while True:
            await config.wait_cooldown()

            lock = self._get_lock()
            async with lock:
                now = time.time()
                if self._burst_remaining > 0:
                    self._burst_remaining -= 1
                    scheduled_time = now
                    if self._burst_remaining == 0:
                        self.next_call = now + self.interval
                else:
                    scheduled_time = max(now, self.next_call)
                    self.next_call = scheduled_time + self.interval

            sleep_duration = scheduled_time - now
            if sleep_duration > 0:
                await asyncio.sleep(sleep_duration + (random.randrange(-5, 5) / 10))

            if config.get_cooldown_remaining() <= 0:
                break

    def reset(self):
        self.next_call = 0.0
        self._burst_remaining = self.burst
