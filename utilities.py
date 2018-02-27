import functools
import random
import time


def timing(func):
    """Function decorator which prints the time in milliseconds for which `func` ran"""
    @functools.wraps(func)
    def wrapper(*args):
        start = time.monotonic()
        return_value = func(*args)
        end = time.monotonic()
        print("Function '{}' took {:.2f} ms".format(func.__name__, (end - start) * 1000.0))
        return return_value
    return wrapper


def weighted_choice(sequence, weights):
    """Return a random element from `sequence`, where each element in `sequence` is weighted by the corresponding
    element in `weights`.

    `Sequence` must be non-empty. `Weights` must be the same length as `sequence`.

    >>> weighted_choice([1, 2], [1, 0])
    1
    >>> weighted_choice([1, 2], [0, 0])
    2
    """

    if len(sequence) <= 0:
        raise ValueError('Sequence must be non-empty')
    if len(sequence) != len(weights):
        raise ValueError('Sequence and weights must have same length')

    total = sum(weights)
    r = random.uniform(0, total)
    # Documentation for random.uniform says: r may or may not be total, depending on floating-point rounding
    if r == total:
        return sequence[-1]
    index = 0
    while r >= 0:
        r -= weights[index]
        index += 1
    return sequence[index - 1]


def clamp(n, smallest, largest):
    """The value of `n` clamped to the range [`smallest`, `largest`]

    >>> clamp(1, 4, 10)
    4
    >>> clamp(12, 4, 10)
    10
    """
    return max(smallest, min(n, largest))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
