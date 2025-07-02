# src/infrastructure/concurrency/task_executor.py
# 增强版本 - 支持更高效的异步执行和动态调优

import logging
from enum import Enum, auto
from typing import List, Callable, TypeVar, Any

from src.infrastructure.concurrency.process_pool import ProcessPool
from src.infrastructure.concurrency.thread_pool import ThreadPool

T = TypeVar("T")

class ExecutionMode(Enum):
    SEQUENTIAL = auto()
    MULTITHREAD = auto()
    MULTIPROCESS = auto()

class TaskExecutor:
    def __init__(self, mode: ExecutionMode, max_workers: int = None):
        self.mode = mode
        self.max_workers = max_workers
        self.logger = logging.getLogger("infrastructure.task_executor")
        
        if self.mode == ExecutionMode.MULTITHREAD:
            self.pool = ThreadPool(max_workers)
        elif self.mode == ExecutionMode.MULTIPROCESS:
            self.pool = ProcessPool(max_workers)
        else:
            self.pool = None

    def execute(self, tasks: List[Callable[[], T]]) -> List[T]:
        task_count = len(tasks)
        self.logger.info(f"Executing {task_count} tasks in {self.mode.name} mode")
        
        if self.mode == ExecutionMode.SEQUENTIAL:
            return [task() for task in tasks]
        else:
            return self.pool.execute_tasks(tasks)

    def execute_with_progress(self, tasks: List[Callable[[], T]], progress_callback: Callable[[int, int], Any] = None) -> List[T]:
        task_count = len(tasks)
        self.logger.info(f"Executing {task_count} tasks with progress in {self.mode.name} mode")
        
        if self.mode == ExecutionMode.SEQUENTIAL:
            results = []
            for i, task in enumerate(tasks):
                result = task()
                results.append(result)
                if progress_callback:
                    progress_callback(i + 1, task_count)
            return results
        else:
            # For thread/process pools, use execute_tasks and manually call progress_callback
            results = []
            futures = self.pool.execute_tasks(tasks)
            for i, result in enumerate(futures):
                results.append(result)
                if progress_callback:
                    progress_callback(i + 1, task_count)
            return results

    def submit_async(self, tasks: List[Callable[[], T]]) -> List[Any]:
        """
        Submit tasks asynchronously and return a list of Future objects.
        
        Args:
            tasks: List of callable tasks
            
        Returns:
            List of Future objects
        """
        task_count = len(tasks)
        self.logger.info(f"Submitting {task_count} tasks asynchronously in {self.mode.name} mode")
        
        if self.mode == ExecutionMode.SEQUENTIAL:
            from concurrent.futures import Future
            futures = []
            for i, task in enumerate(tasks):
                future = Future()
                try:
                    result = task()
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                futures.append(future)
            return futures
        else:
            return self.pool.submit_tasks(tasks)

    def change_mode(self, new_mode: ExecutionMode, max_workers: int = None):
        """
        Change execution mode dynamically.

        Args:
            new_mode: New ExecutionMode
            max_workers: Optional new max_workers value
        """
        self.logger.info(f"Changing execution mode from {self.mode.name} to {new_mode.name}")
        self.mode = new_mode

        if max_workers is not None:
            self.max_workers = max_workers

        if self.mode == ExecutionMode.MULTITHREAD:
            self.pool = ThreadPool(self.max_workers)
        elif self.mode == ExecutionMode.MULTIPROCESS:
            self.pool = ProcessPool(self.max_workers)
        else:
            self.pool = None
