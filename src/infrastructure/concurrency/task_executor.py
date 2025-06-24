# src/infrastructure/concurrency/task_executor.py
import logging
from typing import List, Callable, Any, TypeVar, Dict, Optional, Union
from enum import Enum, auto

# Import pool implementations
from .thread_pool import ThreadPool
from .process_pool import ProcessPool

T = TypeVar('T')  # Return type of tasks

class ExecutionMode(Enum):
    """Execution modes for the task executor."""
    SEQUENTIAL = auto()  # Execute tasks one at a time
    THREADED = auto()    # Execute tasks in parallel using threads
    MULTIPROCESS = auto() # Execute tasks in parallel using processes


class TaskExecutor:
    """
    Unified interface for executing tasks in different concurrency modes.
    """
    def __init__(self, mode: ExecutionMode = ExecutionMode.THREADED, 
                max_workers: Optional[int] = None):
        """
        Initialize the task executor.
        
        Args:
            mode: Execution mode (sequential, threaded, multiprocess)
            max_workers: Maximum number of workers (default: CPU count)
        """
        self.logger = logging.getLogger(__name__)
        self.mode = mode
        self.max_workers = max_workers
        
        # Initialize the appropriate executor based on mode
        if mode == ExecutionMode.THREADED:
            self.pool = ThreadPool(max_workers=max_workers)
        elif mode == ExecutionMode.MULTIPROCESS:
            self.pool = ProcessPool(max_workers=max_workers)
        else:
            self.pool = None  # No pool needed for sequential execution
            
        self.logger.info(f"Initialized TaskExecutor in {mode.name} mode")
        
    def execute(self, tasks: List[Callable[[], T]]) -> List[T]:
        """
        Execute a list of tasks using the configured execution mode.
        
        Args:
            tasks: List of callable tasks (functions with no parameters)
            
        Returns:
            List of results in the order tasks were submitted
        """
        task_count = len(tasks)
        self.logger.debug(f"Executing {task_count} tasks in {self.mode.name} mode")
        
        if self.mode == ExecutionMode.SEQUENTIAL:
            # Execute tasks sequentially
            results = []
            for i, task in enumerate(tasks):
                try:
                    result = task()
                    results.append(result)
                    self.logger.debug(f"Task {i+1}/{task_count} completed successfully")
                except Exception as e:
                    self.logger.error(f"Task {i+1}/{task_count} failed: {str(e)}")
                    raise
            return results
        else:
            # Use the pool for parallel execution
            return self.pool.execute_tasks(tasks)
            
    def execute_with_progress(self, tasks: List[Callable[[], T]], 
                             progress_callback: Callable[[int, int], None]) -> List[T]:
        """
        Execute tasks with progress tracking.
        
        Args:
            tasks: List of callable tasks
            progress_callback: Function called when a task completes (completed_count, total_count)
            
        Returns:
            List of results in the order tasks were submitted
        """
        task_count = len(tasks)
        
        if self.mode == ExecutionMode.SEQUENTIAL:
            # Execute tasks sequentially with progress updates
            results = []
            for i, task in enumerate(tasks):
                try:
                    result = task()
                    results.append(result)
                    progress_callback(i+1, task_count)
                except Exception as e:
                    self.logger.error(f"Task {i+1}/{task_count} failed: {str(e)}")
                    raise
            return results
        elif self.mode == ExecutionMode.THREADED:
            # Thread pool supports progress tracking
            return self.pool.execute_tasks_with_progress(tasks, progress_callback)
        else:
            # Process pool doesn't have progress tracking, fall back to regular execution
            # and update progress at the end
            results = self.pool.execute_tasks(tasks)
            progress_callback(task_count, task_count)
            return results
            
    def change_mode(self, mode: ExecutionMode, max_workers: Optional[int] = None):
        """
        Change the execution mode.
        
        Args:
            mode: New execution mode
            max_workers: Optional new max_workers value
        """
        if mode == self.mode and (max_workers is None or max_workers == self.max_workers):
            # No change needed
            return
            
        # Update settings
        self.mode = mode
        if max_workers is not None:
            self.max_workers = max_workers
            
        # Recreate the pool if needed
        if mode == ExecutionMode.THREADED:
            self.pool = ThreadPool(max_workers=self.max_workers)
        elif mode == ExecutionMode.MULTIPROCESS:
            self.pool = ProcessPool(max_workers=self.max_workers)
        else:
            self.pool = None
            
        self.logger.info(f"Changed execution mode to {mode.name}")