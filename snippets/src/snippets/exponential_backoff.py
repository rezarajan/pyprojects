import time
import random


def exponential_backoff(
    operation, max_retries=5, base_delay=1, max_delay=60, jitter=True
):
    """
    Retries a given operation with exponential backoff.

    Args:
        operation: A callable that performs the operation.
        max_retries (int): Maximum number of retry attempts.
        base_delay (float): Initial delay in seconds.
        max_delay (float): Maximum delay between retries.
        jitter (bool): Whether to add random jitter to the delay.

    Returns:
        The result of the operation if successful.

    Raises:
        The last exception raised by the operation if all retries fail.
    """
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise  # re-raise the last exception
            delay = min(base_delay * (2**attempt), max_delay)
            if jitter:
                delay = delay * random.uniform(0.5, 1.5)
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)


# Example usage:
if __name__ == "__main__":

    def flaky_task():
        # Example task that fails randomly
        if random.random() < 0.7:
            raise ValueError("Random failure")
        return "Success!"

    result = exponential_backoff(flaky_task)
    print("Result:", result)
