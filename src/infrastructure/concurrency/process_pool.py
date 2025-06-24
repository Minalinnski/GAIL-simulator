# src/infrastructure/concurrency/process_pool.py

import logging
import concurrent, multiprocessing
import concurrent.futures
from typing import List, Callable, Any, TypeVar, Dict, Optional, Union

T = TypeVar('T')  # Return type of tasks

class ProcessPool:
    """
    Manages a pool of worker processes for CPU-bound tasks.
    """
    def __init__(self, max_workers: Optional[int] = None):
        """
        Initialize the process pool.
        
        Args:
            max_workers: Maximum number of worker processes (defaults to CPU count)
        """
        self.logger = logging.getLogger(__name__)
        # Use CPU count - 1 to leave one core for the main process by default
        cpu_count = multiprocessing.cpu_count()
        self.max_workers = max_workers or max(1, cpu_count - 1)
        self.logger.info(f"Initialized process pool with {self.max_workers} workers")
        
    def execute_tasks(self, tasks: List[Callable[[], T]]) -> List[T]:
        """
        Execute CPU-bound tasks concurrently across multiple processes.
        
        Args:
            tasks: List of callable tasks
            
        Returns:
            List of results in the order tasks were submitted
        """
        self.logger.info(f"Executing {len(tasks)} tasks with {self.max_workers} processes")
        
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks and collect futures
            futures = [executor.submit(task) for task in tasks]
            
            # Wait for all tasks to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Task failed: {str(e)}")
                    raise
                    
        self.logger.info(f"All {len(tasks)} processes completed")
        return results