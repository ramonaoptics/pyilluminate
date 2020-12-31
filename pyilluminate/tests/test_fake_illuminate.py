from pyilluminate.fake_illuminate import FakeIlluminate


def test_defaults():
    light = FakeIlluminate()
    assert light.N_leds == 377
    assert tuple(light.color) == (1, 1, 1)
    assert light.brightness == 1
    assert len(light.led) == 0


def test_set_values():
    light = FakeIlluminate()
    light.led = [1, 2, 90]
    light.color = (85, 10, 1)
    assert tuple(light.color) == (85, 10, 1)
    assert set(light.led) == set([1, 2, 90])


def test_clear():
    light = FakeIlluminate()
    light.led = [1, 2, 90]
    light.color = (85, 10, 1)
    light.clear()
    assert tuple(light.color) == (85, 10, 1)
    assert len(light.led) == 0


def test_fill_array():
    light = FakeIlluminate()
    light.led = [1, 2, 90]
    light.color = (85, 10, 1)
    light.fill_array()
    assert tuple(light.color) == (85, 10, 1)
    assert set(light.led) == set(range(light.N_leds))
