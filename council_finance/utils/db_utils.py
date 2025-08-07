"""Database connection utilities for handling timeouts and reconnections."""

import logging
import time
from django.db import connection, transaction
from django.db.utils import OperationalError, InterfaceError

logger = logging.getLogger(__name__)


def ensure_connection():
    """Ensure database connection is alive, reconnect if needed."""
    try:
        # Test the connection with a simple query
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except (OperationalError, InterfaceError) as e:
        logger.warning(f"Database connection lost: {e}")
        
        # Close the old connection and let Django create a new one
        try:
            connection.close()
        except Exception:
            pass
        
        # Try to reconnect
        try:
            connection.ensure_connection()
            logger.info("Database connection restored")
            return True
        except Exception as e:
            logger.error(f"Failed to restore database connection: {e}")
            return False


def safe_database_operation(operation_func, max_retries=3, backoff_delay=1):
    """
    Execute a database operation with connection health checking and retries.
    
    Args:
        operation_func: Function to execute that performs database operations
        max_retries: Maximum number of retry attempts
        backoff_delay: Initial delay between retries (doubles each time)
        
    Returns:
        Result of operation_func() or None if all retries failed
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            # Ensure connection is healthy
            if not ensure_connection():
                raise OperationalError("Could not establish database connection")
            
            # Execute the operation
            result = operation_func()
            return result
            
        except (OperationalError, InterfaceError) as e:
            last_exception = e
            logger.warning(f"Database operation failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if attempt < max_retries - 1:  # Don't wait after the last attempt
                delay = backoff_delay * (2 ** attempt)  # Exponential backoff
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            
            # Close connection to force reconnect on next attempt
            try:
                connection.close()
            except Exception:
                pass
    
    logger.error(f"Database operation failed after {max_retries} attempts: {last_exception}")
    return None


def chunked_database_operation(queryset, chunk_size=100, operation_func=None):
    """
    Process a large queryset in chunks to avoid connection timeouts.
    
    Args:
        queryset: Django queryset to process
        chunk_size: Number of records to process per chunk
        operation_func: Function to call for each chunk (optional)
        
    Yields:
        Chunks of the queryset
    """
    total_count = queryset.count()
    processed = 0
    
    logger.info(f"Processing {total_count} records in chunks of {chunk_size}")
    
    for start in range(0, total_count, chunk_size):
        end = min(start + chunk_size, total_count)
        
        def get_chunk():
            return list(queryset[start:end])
        
        # Get chunk with connection health checking
        chunk = safe_database_operation(get_chunk)
        if chunk is None:
            logger.error(f"Failed to retrieve chunk {start}-{end}")
            continue
            
        processed += len(chunk)
        logger.info(f"Processing chunk {start}-{end} ({processed}/{total_count}, {processed/total_count*100:.1f}%)")
        
        if operation_func:
            operation_func(chunk)
        else:
            yield chunk
        
        # Brief pause to prevent overwhelming the database
        time.sleep(0.1)


class DatabaseConnectionMonitor:
    """Context manager for monitoring database operations."""
    
    def __init__(self, operation_name="database_operation"):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"Starting {self.operation_name}")
        
        # Ensure connection is healthy at start
        if not ensure_connection():
            raise OperationalError(f"Could not establish connection for {self.operation_name}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            logger.info(f"Completed {self.operation_name} in {duration:.2f}s")
        else:
            if isinstance(exc_val, (OperationalError, InterfaceError)):
                logger.error(f"Database connection error in {self.operation_name} after {duration:.2f}s: {exc_val}")
            else:
                logger.error(f"Error in {self.operation_name} after {duration:.2f}s: {exc_val}")