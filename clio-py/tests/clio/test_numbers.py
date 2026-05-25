from clio.numbers import floor_to_zero, ceil_to_zero


def test_floor_to_zero():
    assert 10 == floor_to_zero(10.1)
    assert 12 == floor_to_zero(12.9)
    assert -10 == floor_to_zero(-10.1)
    assert -12 == floor_to_zero(-12.9)

    assert 11100 == floor_to_zero(11111, step=100)
    assert 11200 == floor_to_zero(11299, step=100)
    assert -11100 == floor_to_zero(-11111, step=100)
    assert -11200 == floor_to_zero(-11299, step=100)

    assert 11 == floor_to_zero(10.999, epsilon=0.01)
    assert -11 == floor_to_zero(-10.999, epsilon=0.01)


def test_ceil_to_zero():
    assert 11 == ceil_to_zero(10.1)
    assert 13 == ceil_to_zero(12.9)
    assert -11 == ceil_to_zero(-10.1)
    assert -13 == ceil_to_zero(-12.9)

    assert 11200 == ceil_to_zero(11111, step=100)
    assert 11300 == ceil_to_zero(11299, step=100)
    assert -11200 == ceil_to_zero(-11111, step=100)
    assert -11300 == ceil_to_zero(-11299, step=100)

    assert 11 == ceil_to_zero(11.0001, epsilon=0.01)
    assert -11 == ceil_to_zero(-11.0001, epsilon=0.01)
