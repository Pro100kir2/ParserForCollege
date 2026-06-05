import asyncio
from typing import List, Callable
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AsyncWorkerPool:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.semaphore = asyncio.Semaphore(max_workers)
    
    async def process_chunk(self, items: List, processor: Callable, chunk_size: int = 1000):
        tasks = []
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            task = asyncio.create_task(self._process_with_semaphore(chunk, processor))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_results = []
        errors = []
        
        for result in results:
            if isinstance(result, Exception):
                errors.append(result)
                logger.error(f"Worker error: {str(result)}")
            else:
                if isinstance(result, list):
                    successful_results.extend(result)
                else:
                    successful_results.append(result)
        
        return successful_results, errors
    
    async def _process_with_semaphore(self, chunk: List, processor: Callable):
        async with self.semaphore:
            try:
                if asyncio.iscoroutinefunction(processor):
                    return await processor(chunk)
                else:
                    return processor(chunk)
            except Exception as e:
                logger.error(f"Error processing chunk: {str(e)}")
                raise


async def process_files_async(files: List[str], processor: Callable, max_workers: int = 4, chunk_size: int = 1000):
    pool = AsyncWorkerPool(max_workers)
    return await pool.process_chunk(files, processor, chunk_size)
