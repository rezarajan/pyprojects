import pytest
from drone_delivery import drone_delivery


# NOTE: test inputs can be parameterized using pytest
@pytest.mark.parametrize(
    "stations, target, expected",
    [
        ([7, 4, 14], 23, 4),  # 4 steps walked
        ([7, 4, 14], 25, 25),  # 25 steps walked
        ([0, 2, 3], 5, 0),  # 0 steps walked
        ([28, 18, 15, 8, 3, 0], 25, 0),  # 0 steps walked
        ([25, 8, 3, 0], 25, 25),  # 25 steps walked
    ],
)
def test_solution(stations, target, expected):
    assert drone_delivery.solve(stations, target) == expected
