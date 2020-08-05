from pyilluminate import Illuminate
import pytest


pytestmark = pytest.mark.device


serial_number = Illuminate.list_all_serial_numbers()
ports = Illuminate.find()


@pytest.mark.parametrize('port', ports)
def test_open_by_port(port):
    light = Illuminate(port=port)
    assert light.serial.port == port
    light.close()


def test_open():
    light = Illuminate()
    light.close()


@pytest.mark.parametrize('serial_number', ['4916510', '4725300'])
def test_open_serial_number(serial_number):
    try:
        light = Illuminate(serial_number=serial_number)
    except RuntimeError:
        pytest.skip('Device not connected')

    connected_serial_number = light.serial_number
    light.close()
    assert connected_serial_number == serial_number


@pytest.mark.parametrize('serial_number', ['4916510', '4725300'])
def test_device_by_serial_number(serial_number):
    device_pairs = Illuminate._device_serial_number_pairs(
        serial_numbers=[serial_number])

    assert len(device_pairs) in (0, 1)
    if len(device_pairs) == 0:
        pytest.skip('Device not connected')
    assert device_pairs[0][1] == serial_number
