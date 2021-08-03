from pyilluminate import Illuminate
from pyilluminate.fake_illuminate import FakeIlluminate
import pytest
from numpy.testing import assert_array_almost_equal


@pytest.fixture(
    scope='function',
    params=[
        pytest.param(True, marks=pytest.mark.device),
        False
    ])
def light(request):
    if request.param:
        light = Illuminate()
    else:
        light = FakeIlluminate()
    yield light
    light.close()


def test_low_value(light):
    # maximum value should not exceed 255
    max_brightness = light.find_max_brightness(num_leds=1)
    assert_array_almost_equal(max_brightness, (255.0, 255.0, 255.0), decimal=5)
    max_brightness = light.find_max_brightness(num_leds=1,
                                               color_ratio=(0.25, 0.25, 0.5))
    assert_array_almost_equal(max_brightness, (127.5, 127.5, 255.0), decimal=5)


def test_high_value(light):
    max_brightness = light.find_max_brightness(655, color_ratio=(1, 1, 1))
    goal_brightness = (
        51.90839694656488,
        51.90839694656488,
        51.90839694656488,
    )
    assert_array_almost_equal(max_brightness, goal_brightness, decimal=5)


def test_ratios(light):
    max_brightness = light.find_max_brightness(655, (3, 2, 1))
    goal_brightness = (
        77.86259541984732,
        51.90839694656488,
        25.95419847328244,
    )
    assert_array_almost_equal(max_brightness, goal_brightness, decimal=5)

    max_brightness = light.find_max_brightness(655, (6, 4, 2))
    assert_array_almost_equal(max_brightness, goal_brightness, decimal=5)

    light.color = (3, 2, 1)
    max_brightness = light.find_max_brightness(655)
    goal_brightness = (
        77.86259541984732,
        51.90839694656488,
        25.95419847328244,
    )
    assert_array_almost_equal(max_brightness, goal_brightness, decimal=5)
