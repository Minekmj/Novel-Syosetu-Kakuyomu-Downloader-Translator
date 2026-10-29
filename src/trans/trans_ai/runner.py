import asyncio
from .config import ForceStopException


async def run_worker_pool(workers, worker_fn, check_i):
    worker_tasks = []
    for worker in workers:
        for worker_number in range(worker.max_concurrent):
            worker_tasks.append(asyncio.create_task(worker_fn(worker, worker_number + 1)))

    async def force_stop_watcher():
        while True:
            if check_i and check_i():
                for t in worker_tasks:
                    if not t.done():
                        t.cancel()
                return
            await asyncio.sleep(0.05)

    watcher_task = asyncio.create_task(force_stop_watcher())

    try:
        await asyncio.gather(*worker_tasks)
    except asyncio.CancelledError:
        raise ForceStopException()
    finally:
        watcher_task.cancel()