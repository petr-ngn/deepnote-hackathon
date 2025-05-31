"""
Utility functions for YAML loading, exponential backoff, and job completion waiting.
"""
import time
import random
import logging
from pathlib import Path
from functools import wraps
from typing import Dict, Any
import yaml
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def exponential_backoff(
        max_retries: int = 5,
        base_delay: int = 1,
        max_delay: int = 60,
):
    """
    Decorator to apply exponential backoff with jitter for retrying operations
    that may raise a ThrottlingException when invoking AWS services.
    Args:
        max_retries (int): Maximum number of retry attempts.
        base_delay (int): Base delay in seconds for the first retry.
        max_delay (int): Maximum delay in seconds between retries.
    Returns:
        function: Decorated function that implements exponential backoff.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code != 'ThrottlingException':
                        raise  # Don't retry on other errors

                    if attempt >= max_retries:
                        logger.error("Max retries reached. Raising exception.")
                        raise

                    delay = min(max_delay, base_delay * (2 ** attempt))
                    jitter = random.uniform(0, 0.5 * delay)
                    total_delay = delay + jitter

                    logger.warning(
                        "ThrottlingException on attempt %d. Retrying in %.2f seconds...",
                        attempt + 1, total_delay
                    )

                    time.sleep(total_delay)
                    attempt += 1
        return wrapper
    return decorator


def wait_for_completion(
        wait_interval: int = 5,
        max_wait_seconds: int = 150,
):
    """
    Decorator to wait for an AWS job to complete, checking its status at regular intervals.
    Args:
        wait_interval (int): Time in seconds to wait between status checks.
        max_wait_seconds (int): Maximum time in seconds to wait for job completion.
    Returns:
        function: Decorated function that waits for job completion.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            while True:
                result = func(*args, **kwargs)

                if result["JobStatus"] in ("SUCCEEDED", "FAILED"):
                    return result

                if time.time() - start_time > max_wait_seconds:
                    raise TimeoutError(
                        f"{func.__name__} did not complete within {max_wait_seconds} seconds."
                    )

                time.sleep(wait_interval)
        return wrapper
    return decorator


def _load_config(yaml_path: str) -> dict:
    """
    Load a YAML configuration file.
    
    Args:
        yaml_path (str): Path to the YAML file.
    
    Returns:
        dict: Parsed YAML content as a dictionary.
    """
    with open(yaml_path, 'r', encoding = 'utf-8') as file:
        return yaml.safe_load(file)

def _load_configs(
        config_dir: str,
) -> Dict[str, Any]:
    """
    Load all YAML configuration files from a specified directory.
    Args:
        config_dir (str): Path to the directory containing YAML files.
    Returns:
        Dict[str, Any]: A dictionary where keys are file names (without extension)
                        and values are the parsed YAML content.
    """
    config_dir_path = Path(config_dir)

    config_files = [
        f for f in config_dir_path.iterdir()
        if f.is_file() and f.suffix == '.yaml'
    ]

    configs = {
            file.stem: _load_config(
                f"{config_dir}/{file.name}"
            )
            for file in config_files
    }

    return configs
