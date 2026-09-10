from app import calculate_total


def test_calculate_total() -> None:
    assert calculate_total(100.0, 18.0) == 118.0
