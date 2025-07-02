import concurrent.futures
import logging
from typing import Callable, List, TypeVar, Any

T = TypeVar("T")

class ThreadPool:
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers
        self.logger = logging.getLogger("infrastructure.thread_pool")

    def execute_tasks(self, tasks: List[Callable[[], T]]) -> List[T]:
        self.logger.info(f"Executing {len(tasks)} tasks with {self.max_workers} workers")
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(task) for task in tasks]
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
        return results

    def submit_tasks(self, tasks: List[Callable[[], T]]) -> List[concurrent.futures.Future]:
        """
        Submit tasks to thread pool asynchronously without waiting for results.
        Returns list of Future objects.
        """
        self.logger.info(f"Submitting {len(tasks)} tasks asynchronously with {self.max_workers} workers")
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        futures = [executor.submit(task) for task in tasks]
        return futures