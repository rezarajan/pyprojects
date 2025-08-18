from math import isclose as _isclose
from poisson.core import poisson, lt_poisson, gt_poisson, leq_poisson, geq_poisson

# Tolerance for floating-point comparisons (5 decimal places)
TOL = 1e-4


def isclose(a: float, b: float) -> float:
    """Shadows math.isclose with the included tolerance"""
    return _isclose(a, b, rel_tol=TOL)


def test_poisson():
    assert isclose(poisson(5, 3), 0.14037)
    assert isclose(poisson(10, 5), 0.03783)


def test_lt_poisson():
    assert isclose(lt_poisson(5, 3), 0.12465)
    assert isclose(lt_poisson(10, 5), 0.02925)


def test_gt_poisson():
    assert isclose(gt_poisson(5, 3), 0.73497)
    assert isclose(gt_poisson(10, 5), 0.93291)


def test_leq_poisson():
    assert isclose(leq_poisson(5, 3), 0.26503)
    assert isclose(leq_poisson(10, 5), 0.06709)


def test_geq_poisson():
    assert isclose(geq_poisson(5, 3), 0.87535)
    assert isclose(geq_poisson(10, 5), 0.97075)
