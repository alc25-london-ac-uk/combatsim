import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Optional, Sequence

DEFAULT_WORKER_FRACTION = 0.7

def default_worker_count() -> int:
    return max(1, round((os.cpu_count() or 2) * DEFAULT_WORKER_FRACTION))

def run_jobs_in_parallel(worker: Callable[[Any], Any], jobs: Sequence[Any], max_workers: Optional[int] = None, progress: bool = False) -> list:
    if max_workers is not None and max_workers < 1:
        raise ValueError("max_workers must be at least 1")

    jobs = list(jobs)
    results: list = [None] * len(jobs)
    if not jobs:
        return results

    workers = min(max_workers or default_worker_count(), len(jobs))
    finished = 0

    def note_finished() -> None:
        nonlocal finished
        finished += 1
        if progress:
            print(f"  [{finished}/{len(jobs)}] jobs finished", file = sys.stderr, flush = True)

    if workers == 1:
        for index, job in enumerate(jobs):
            results[index] = worker(job)
            note_finished()
        return results

    with ProcessPoolExecutor(max_workers = workers) as pool:
        futures = {pool.submit(worker, job): index for index, job in enumerate(jobs)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
            note_finished()

    return results
