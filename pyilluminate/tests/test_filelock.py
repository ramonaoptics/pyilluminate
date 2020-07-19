from pyilluminate import Illuminate
import pytest

pytestmark = pytest.mark.device


def tests_filelock_multiBoard():

    light = Illuminate()

    with pytest.raises(RuntimeError):
        Illuminate(serial_number=light.serial_number)

    light.close()


def tests_filelock_singleBoard():

    light = Illuminate()

    with pytest.raises(RuntimeError):
        Illuminate()

    light.close()
