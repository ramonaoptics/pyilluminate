from pyilluminate import Illuminate
import numpy as np
import pytest

pytestmark = pytest.mark.device


@pytest.fixture(scope='module')
def light():
    with Illuminate() as light:
        yield light


def test_single_led_command(light):
    light.color = 1
    # setting led with an integer
    light.led = 30


def test_short_led_command(light):
    light.color = 1
    light.led = range(30, 60)


def test_short_led_command_list(light):
    light.color = 1
    light.led = list(range(30, 60))


def test_short_led_command_array(light):
    light.color = 1
    light.led = np.arange(30, 60, dtype=int)


def test_long_led_command(light):
    light.color = 1
    # This command is often longer than the internal buffer of the system
    # Therefore, without the ability to split up long commands, the teensy
    # may hang
    light.led = range(609)
