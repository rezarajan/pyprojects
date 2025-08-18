# Poisson Calculator Helper Functions
from math import pow, factorial, e


def poisson(lam: float, k: int) -> float:
    """Returns the probability of obtaining k successes in a poisson experiment.
    lam: average number of successes in a fixed time interval
    k: number of successes
    """
    return pow(lam, k) * pow(e, -lam) / factorial(k)


def lt_poisson(lam: float, k: int) -> float:
    """Returns the probability of obtaining *fewer than k* successes in a poisson experiment.
    lam: average number of successes in a fixed time interval
    k: number of successes
    """

    p = 0
    for i in range(k):
        p += poisson(lam, i)

    return p


def gt_poisson(lam: float, k: int) -> float:
    """Returns the probability of obtaining *more than k* successes in a poisson experiment.
    lam: average number of successes in a fixed time interval
    k: number of successes
    """

    return 1 - lt_poisson(lam, k + 1)


def leq_poisson(lam: float, k: int) -> float:
    """Returns the probability of obtaining *k or less* successes in a poisson experiment.
    lam: average number of successes in a fixed time interval
    k: number of successes
    """

    return lt_poisson(lam, k + 1)


def geq_poisson(lam: float, k: int) -> float:
    """Returns the probability of obtaining *k or more* successes in a poisson experiment.
    lam: average number of successes in a fixed time interval
    k: number of successes
    """

    return 1 - lt_poisson(lam, k)
