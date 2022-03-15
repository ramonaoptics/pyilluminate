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


def test_set_leds_to_zero(light):
    color = (1, 2, 3)
    expected_leds = []

    assert expected_leds == light.led

    light.color = color
    light.led = [1, 2, 3]
    expected_leds = [1, 2, 3]

    assert expected_leds == light.led

    light.autoclear = False
    light.led = [3, 4]
    assert [1, 2, 3, 4] == light.led

    # Turn OFF some LEDs by setting the PWM to 0% duty cycle
    light.color = 0
    light.led = [2, 4, 6]
    assert [1, 3] == light.led
