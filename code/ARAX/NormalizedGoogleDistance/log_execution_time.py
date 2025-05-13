import time
import logging
from contextlib import contextmanager


def log_execution_time(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        logging.debug(f"Executed {func.__name__} in {elapsed_time:.10f} seconds")
        return result

    return wrapper


@contextmanager
def log_block_execution_time(block_name):
    start_time = time.time()
    yield
    end_time = time.time()
    elapsed_time = end_time - start_time
    logging.debug(f"Executed {block_name} in {elapsed_time:.10f} seconds")



    # import logging
    # import os
    #
    # log_file_path = os.path.abspath('performance.log')
    #
    # # Create a logger
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)
    #
    # # Create a file handler
    # handler = logging.FileHandler(log_file_path)
    # handler.setLevel(logging.DEBUG)
    #
    # # Create a logging format
    # formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')
    # handler.setFormatter(formatter)
    #
    # # Add the handlers to the logger
    # logger.addHandler(handler)
    #
    # # Test logging
    # logger.debug("Adalimumab-UC test has been started")
