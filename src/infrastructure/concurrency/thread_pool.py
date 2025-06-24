# src/infrastructure/concurrency/thread_pool.py
import logging
import multiprocessing
import concurrent.futures
from typing import List, Callable, Any, Dict, TypeVar, Generic, Optional

T = TypeVar('T')  # Return type of tasks


class ThreadPool:
    """
    Manages a pool of worker threads for executing tasks concurrently.
    """
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the thread pool.
        
        Args:
            max_workers: Maximum number of worker threads (defaults to CPU count)
        """
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.logger.info(f"Initialized thread pool with {self.max_workers} workers")
        
    def execute_tasks(self, tasks: List[Callable[[], T]]) -> List[T]:
        """
        Execute a list of tasks concurrently.
        
        Args:
            tasks: List of callable tasks (functions with no parameters)
            
        Returns:
            List of results in the order tasks were submitted
        """
        results = []
        task_count = len(tasks)
        
        self.logger.info(f"Executing {task_count} tasks with {self.max_workers} workers")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = [executor.submit(task) for task in tasks]
            
            # Get results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                try:
                    result = future.result()
                    results.append(result)
                    self.logger.debug(f"Task {i+1}/{task_count} completed successfully")
                except Exception as e:
                    self.logger.error(f"Task {i+1}/{task_count} raised an exception: {str(e)}")
                    # Re-raise the exception
                    raise
        
        self.logger.info(f"All {task_count} tasks completed")
        return results
        
    def execute_tasks_with_progress(self, tasks: List[Callable[[], T]], 
                                   progress_callback: Callable[[int, int], None]) -> List[T]:
        """
        Execute tasks concurrently with progress tracking.
        
        Args:
            tasks: List of callable tasks
            progress_callback: Function called when a task completes (completed_count, total_count)
            
        Returns:
            List of results in the order tasks were submitted
        """
        results = [None] * len(tasks)  # Pre-allocate result list
        task_count = len(tasks)
        completed_count = 0
        
        self.logger.info(f"Executing {task_count} tasks with progress tracking")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map tasks to futures and keep track of their indices
            future_to_index = {executor.submit(task): i for i, task in enumerate(tasks)}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                except Exception as e:
                    self.logger.error(f"Task {index+1}/{task_count} failed: {str(e)}")
                    # Store the exception to be raised later
                    results[index] = e
                
                # Update progress
                completed_count += 1
                progress_callback(completed_count, task_count)
        
        # Check if any tasks failed
        exceptions = [r for r in results if isinstance(r, Exception)]
        if exceptions:
            self.logger.error(f"{len(exceptions)} tasks failed with exceptions")
            raise exceptions[0]  # Raise the first exception
            
        self.logger.info(f"All {task_count} tasks completed successfully")
        return results
