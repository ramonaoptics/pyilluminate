from pyilluminate import Illuminate
from pyilluminate.fake_illuminate import FakeIlluminate
from numpy.testing import assert_array_equal, assert_allclose
import numpy as np
import pytest


@pytest.fixture(
    scope='function',
    params=[
        pytest.param(True, marks=pytest.mark.device),
        False
    ])
def light(request):
    if request.param:
        yield Illuminate()
    else:
        yield FakeIlluminate()


def test_initial_state(light):
    assert len(light.led) == 0
    assert_array_equal(light.led_state.data, 0)


def test_led_and_clear(light):
    color = (2, 3, 4)
    led = [1, 2, 3]
    led_state_expected = np.zeros((light.N_leds, 3))

    light.color = color

    light.led = led
    led_state_expected[led] = color
    assert_array_equal(light.led_state.data, led_state_expected)

    light.clear()
    led_state_expected[...] = 0
    assert_array_equal(light.led_state.data, led_state_expected)

    led = [5, 10, 30]
    color = (9, 8, 1)
    light.color = color
    light.led = led
    led_state_expected[...] = 0
    led_state_expected[led] = color
    assert_array_equal(light.led_state.data, led_state_expected)
    assert set(light.led) == set(led)

    light.autoclear = False

    previous_leds = led
    led = [5, 6, 7, 8]
    color = (1, 1, 1)
    light.color = color
    light.led = led
    # Do not clear the state
    led_state_expected[led] = color
    assert_array_equal(light.led_state.data, led_state_expected)
    assert set(light.led) == set(previous_leds).union(led)

    light.clear()
    led_state_expected[...] = 0
    assert_array_equal(light.led_state.data, led_state_expected)
    assert len(light.led) == 0


def test_fill_array(light):
    color = (2, 3, 1)
    light.color = color
    light.fill_array()
    led_state_expected = np.zeros((light.N_leds, 3))
    led_state_expected[...] = np.asarray(color)
    assert_allclose(light.led_state.data, led_state_expected)
