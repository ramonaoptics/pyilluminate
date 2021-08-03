from pyilluminate import Illuminate
from pyilluminate.fake_illuminate import FakeIlluminate
from time import sleep
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
        with Illuminate() as light:
            yield light
    else:
        with FakeIlluminate() as light:
            yield light


def test_single_color(light):
    light.color = 1
    light.fill_array()
    sleep(1)
    light.clear()


def test_red_color_tuple(light):
    light.color = (1, 0, 0)
    light.fill_array()
    sleep(1)
    light.clear()


def test_blue_color_list(light):
    light.color = (0, 1, 0)
    light.fill_array()
    sleep(1)
    light.clear()


def test_green_color_numpy(light):
    light.color = np.asarray((0, 0, 1))
    light.fill_array()
    sleep(1)
    light.clear()


def test_ir_colors(light):
    light.color = (5, 10, 2)
    assert light.color_940_ir == 7.5  # average of first two values
    assert light.color_850_ir == 2

    light.color_940_ir = 20
    assert light.color == (20, 20, 0)
    assert light.color_940_ir == 20
    assert light.color_850_ir == 0

    light.color_850_ir = 10
    assert light.color == (0, 0, 10)
    assert light.color_940_ir == 0
    assert light.color_850_ir == 10
