from pyilluminate import Illuminate
import pytest


pytestmark = pytest.mark.device


def test_open_by_port():
    ports = Illuminate.find()
    light = Illuminate(port=ports[0])
    light.close()


def test_open_by_serial_number():
    serial_numbers = Illuminate.list_all_serial_numbers()
    light = Illuminate(serial_number=serial_numbers[0])
    light.close()


def test_open():
    light = Illuminate()
    light.close()
