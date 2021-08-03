from pyilluminate import Illuminate
from time import sleep
import numpy as np
import pytest

pytestmark = pytest.mark.device


@pytest.fixture(scope='module')
def light():
    with Illuminate() as light:
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
