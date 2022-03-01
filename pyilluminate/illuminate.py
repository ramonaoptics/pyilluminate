import json
import re
from time import sleep
from warnings import warn
from typing import List, Union, Optional, Iterable, Tuple
import collections
from packaging.version import Version

import xarray as xr

import numpy as np
from serial import Serial, SerialException
from serial.tools.list_ports import comports
from multiuserfilelock import MultiUserFileLock, tmpdir, Timeout
from pathlib import Path

locks_dir = Path(tmpdir) / 'pyilluminate'

"""
Trigger notes from Zack's code.

Triggers represents the trigger output from each trigger pin on the teensy.
The modes can be:
0 : No triggering
1 : Trigger at start of frame
2 : Trigger each update of pattern

"""

known_devices = [
    {   # Example device structure
        'serial_number': 'XXXXXXX',
        'device_name': 'some_board_name',
        'mac_address': '01:23:45:67:89:AB',
    },
]

known_serial_numbers = [
    d['serial_number']
    for d in known_devices
    if d['serial_number']  # empty strings and NULL are Falsy
]
known_mac_addresses = {
    d['mac_address']: d['serial_number']
    for d in known_devices
}


# Typically defined in commandrouting.h
# Increasing this causes more errors in the firmware
# I'm not too sure, but for some reason setting this number above
# 64 makes communication fail.
# https://forum.pjrc.com/threads/54773-Inreasing-USB-Serial-Buffer-Teensy-3-2
MAX_ARGUMENT_CHAR_COUNT = 64 * 1


def get_port_serial_number(port):
    coms = comports()
    for c in coms:
        if c.device == port:
            return c.serial_number

    else:
        raise ValueError(f"Did not find the requested port: {port}")


class Illuminate:
    """Controlls a SciMicroscopy Illuminate board."""

    VID_PID_s = [
        (0x16C0, 0x0483),
    ]
    __slots__ = [
        '_use_lock',
        '_lock',
        'serial',
        '_led_positions',
        '_help',
        '_led_state',
        '_led_cache',
        '_maximum_current',
        '_color',
        '_mac_address',
        '_interface_bit_depth',
        '_precision',
        'serial_number',
        'reboot_on_start',
        'N_leds',
        '_device_name',
        '_part_number',
        '_serial_number',
        '_led_count',
        '_sequence_bit_depth',
        '_has_autoupdate',
        '_autoclear',
        '_autoupdate',
        '_scale_factor'
    ]
    _known_device = known_devices
    _known_serial_numbers = known_serial_numbers
    _known_mac_addresses = known_mac_addresses

    @staticmethod
    def find(serial_numbers=None):
        """Find all the serial ports that are associated with Illuminate.

        Parameters
        ----------
        serial_numbers: list of str, or None
            If provided, will only match the serial numbers that are contained
            in the provided list.

        Returns
        -------
        devices: list of serial devices
            List of serial devices

        Note
        ----
        If a list of serial numbers is not provided, then this function may
        match Teensy 3.1/3.2 microcontrollers that are connected to the
        computer but that may not be associated with the Illuminate boards.

        """
        pairs = Illuminate._device_serial_number_pairs(
            serial_numbers=serial_numbers)
        if len(pairs) == 0:
            return []
        devices, _ = zip(*pairs)
        return devices

    @staticmethod
    def list_all_serial_numbers(serial_numbers=None):
        """Find all the currently connected Illuminate serial numbers.

        Parameters
        ----------
        serial_numbers: list of str, or None
            If provided, will only match the serial numbers that are contained
            in the provided list.

        Returns
        -------
        serial_numbers: list of serial numbers
            List of connected serial numbers.

        Note
        ----
        If a list of serial numbers is not provided, then this function may
        match Teensy 3.1/3.2 microcontrollers that are connected to the
        computer but that may not be associated with the Illuminate boards.

        """
        pairs = Illuminate._device_serial_number_pairs(
            serial_numbers=serial_numbers)
        if len(pairs) == 0:
            return []
        _, serial_numbers = zip(*pairs)
        return serial_numbers

    @staticmethod
    def _device_serial_number_pairs(serial_numbers=None):
        com = comports()
        pairs = [
            (c.device, c.serial_number)
            for c in com
            if ((c.vid, c.pid) in Illuminate.VID_PID_s and
                (serial_numbers is None or
                 c.serial_number in serial_numbers))
        ]

        return pairs

    def __init__(self, *, port: str=None, reboot_on_start: bool=True,
                 baudrate: int=115200, timeout: float=0.500,
                 open_device: bool=True, mac_address: str=None,
                 serial_number: str=None,
                 precision=8, use_lock=True, maximum_current=8,) -> None:
        """Open the Illumination board.

        Parameters
        ----------
        port: string
            On Windows, this is something like ``'COM4'``.
            On Linux, this is something like ``'/dev/ttyUSB0'``.
        reboot_on_start: bool
            This will cause the microcontroller to reboot itself, sending
            all the configuration commands to the shift registers as needed.
        baudrate: int
            Set to the manufacturer specifications.
        timeout: float (seconds)
            A timeout before giving up on receiving commands. A sensible value
            is something above 400 ms.
        open_device: bool
            If True, the __init__ function call will open the device. If false,
            a manual call to ``open`` needs to be issued.
        serial_number:
            This is the serial number of the teensy USB controller. Only
            one serial_number will be addressed at a time.
        precision: int, 0, 8 or 16
            Color precision to use when setting the LED color. Valid values
            include 8 and 16 bit. Setting a value of 0 indicates that numbers
            between 0 and 1 are used.
        use_lock: bool
            If set to False, a lock will not be used to secure the connection.
        maximum_current: int
            The maximum current limit to be set on the illumination board.

        """
        # Create objects that we assume exist
        self._use_lock = use_lock
        self._lock = None
        self.serial = None
        self._led_positions = None
        self._help = None
        self._led_state = None
        self._led_cache = []
        self._maximum_current = maximum_current

        # Create default values for device parameters
        self._color = (0, 0, 0)
        self._mac_address = ""
        self._interface_bit_depth = 8
        if port is not None and serial_number is None:
            serial_number = get_port_serial_number(port)

        if timeout < 0.4:
            warn('Timeout too small, try providing at least 0.5 seconds.')

        self._precision = precision

        if mac_address is not None:
            serial_number = self.serial_by_mac_address(mac_address)
            warn(f'The parameter mac_address is deprecated and will be '
                 f'removed in a future version. Use the parameter '
                 f'serial_number instead. The serial number associated '
                 f'with the device with mac_address="{mac_address}" is '
                 f'"{serial_number}".', stacklevel=2)

        self.serial_number = serial_number

        self.reboot_on_start = reboot_on_start
        # Explicitely provide None to the port so as to delay opening
        # the device until the very end of the setup
        self.serial = Serial(port=None,
                             baudrate=baudrate, timeout=timeout,
                             exclusive=True)
        # Make the buffer size really large since the LED positions,
        # communicated as a JSON string take quite a few characters to send
        if hasattr(self.serial, 'set_buffer_size'):
            # this doesn't exist on all platforms
            self.serial.set_buffer_size(rx_size=50000)

        if open_device:
            self.open()

    @classmethod
    def serial_by_mac_address(cls, mac_address: str) -> str:
        serial_number = cls._known_mac_addresses.get(mac_address, None)
        if serial_number is not None:
            return serial_number
        else:
            raise RuntimeError(
                f"mac_address {mac_address} is not known, use serial number. "
                f"Contact info@ramonaoptics.com providing the mac_address and "
                f"serial number combination."
            )

    @property
    def device_name(self):
        """The human readable name of the device."""
        return self._device_name

    def _load_parameters(self) -> None:
        """Read the parameters from the illuminate board.

        Function is called automatically when the device is opened.
        """
        p_raw = self.parameters_json
        parameters = {
            'interface_bit_depth': 8,
            'mac_address': '',
        }
        loaded_parameters = json.loads(p_raw)
        parameters.update(loaded_parameters)

        self.N_leds = parameters['led_count']
        self._device_name = parameters['device_name']
        self._part_number = parameters['part_number']
        self._serial_number = parameters['serial_number']
        self._led_count = int(parameters['led_count'])  # type: ignore
        # self._center_wavelength
        # self.color_channels
        self._sequence_bit_depth = parameters['bit_depth']
        self._mac_address = str(parameters['mac_address'])  # type: ignore

        self._interface_bit_depth = int(  # type: ignore
            parameters['interface_bit_depth'])  # type: ignore

        # There are a ton of default properties that are not easy to read.
        # Maybe I can get Zack to implement reading them, but I'm not sure if
        # that will be possible.

        led_state = xr.DataArray(
            np.zeros((self.N_leds, 3)),
            dims=['led_number', 'rgb'],
            coords={'led_number': np.arange(self.N_leds),
                    'rgb': ['r', 'g', 'b']})
        led_state['precision'] = self.precision
        led_state['firmware_version'] = self.version
        led_state['device_name'] = self.device_name
        led_state['serial_number'] = self.serial_number
        self._led_state = led_state

    def _read_led_positions(self):
        # This method is defined so that other creators of LED boards
        # Can redfine it as necessary to optimize various aspects.

        # as dictionary
        # Units at this point are in mm
        # This function faults sometimes, therefore, we assign the result
        # of ask_string to a variable, making debugging a little easier.
        for _ in range(10):
            try:
                # Because the pledpos serial communication can be really large
                # the amount of data might not fit in the buffer on Windows
                # This can cause the JSON data to be malformed, causing a
                # decode error below
                s = self._ask_string('pledpos')
                p = json.loads(s)[
                    'led_position_list_cartesian']
                break
            except json.JSONDecodeError as e:
                error = e
                sleep(0.1)
        else:
            raise error

        led_positions = xr.DataArray(
            np.empty((self.N_leds, 3)),
            dims=['led_number', 'zyx'],
            coords={'led_number': np.arange(self.N_leds),
                    'zyx': ['z', 'y', 'x']})
        led_positions['serial_number'] = self.serial_number
        led_positions['firmware_version'] = self.version
        led_positions['device_name'] = self.device_name
        for key, item in p.items():
            # x, y are provided in units of mm
            # z is provided in units of cm
            key = int(key)
            led_positions[key, 2] = item[0] * 0.001
            led_positions[key, 1] = item[1] * 0.001
            led_positions[key, 0] = item[2] * 0.01

        self._led_positions = led_positions

    @property
    def precision(self):
        """Python interface bitdepth"""
        # TODO: this is a pretty bad word, and we should probably just move
        # toward 16 bit depth at this stage
        return self._precision

    @property
    def led_count(self) -> int:
        return self._led_count

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def _find_port_number(self):
        if self.serial.port is None:
            if self.serial_number is None:
                serial_numbers = None
            else:
                serial_numbers = [self.serial_number]
            available_ports = self._device_serial_number_pairs(
                serial_numbers)
            if len(available_ports) == 0:
                raise RuntimeError("No Illuminate devices found")

            port, serial_number = available_ports[0]
            self.serial.port = port
            self.serial_number = serial_number

    def open(self) -> None:
        if not self.serial.isOpen():
            self._find_port_number()
            self._lock_acquire()
            # 2021/07/19: Mark
            # For some reason, we seem to be hitting problems when we try
            # to open the serial board for the first time.
            # They manifest themselves as decode errors in the json string
            # because the "reboot" command seems to return its status out
            # of order???
            # Our previous tip has been for the end user to
            # "ignore" the first failure, and to attempt to open the
            # LED board a second time.
            #
            # Therefore, we take it upon ourselves attempt to do the open
            # sequence twice

            # Attempt to open the serial board
            try:
                self._open()
            except Exception:
                pass

            # Check to see if it worked or not.
            if self.serial.isOpen():
                return

            # Sleep to allow things to calm down???
            sleep(0.25)

            # Try again, but this time fail if it didn't work
            try:
                self._open()
            except Exception as e:
                self._lock_release()
                raise e

    def _open(self) -> None:
        """Open the serial port. Only useful if you closed it."""
        if not self.serial.isOpen():
            self._find_port_number()
            try:
                self.serial.open()
            except SerialException:
                raise SerialException(
                    "Must close previous Illuminate connection before "
                    "establishing a new one. If there is a previous instance "
                    "of Illuminate either delete the object or call the "
                    "'close' method.")

        try:
            self._open_startup_procedure()
        except Exception:
            self.serial.close()
            raise

        # Reset cached variables
        self._led_positions = None
        self._help = None

        # get/set firmware constants
        self.maximum_current = self._maximum_current

    def _open_startup_procedure(self):
        sleep(0.1)

        self.serial.reset_output_buffer()
        self.serial.reset_input_buffer()
        self.serial.flush()

        if self.serial.in_waiting != 0:
            self.close()
            raise RuntimeError(
                "For some reason there is still some information being sent "
                "to the Illuminate board. Try opening it again, or "
                "reconnecting the cable.")

        if self.reboot_on_start:
            self._led_cache = []
            # This reboot procedure will clear the device
            self.reboot()
        try:
            self._load_parameters()
        except json.JSONDecodeError as e:
            self.close()
            e.args = (('Could not successfully open the Illuminate board.',) +
                      e.args)
            raise e

        version = Version(self.version)
        if version > Version('1.13'):
            self._has_autoupdate = True
        else:
            self._has_autoupdate = False

        # Set it to clear between commands.
        # This may have changed due to the user having previously
        # Opened the Illuminate board, so we set it to a safe default
        self.autoclear = True
        self.autoupdate = True

        if version > Version('1.13') and version < Version('1.21.0'):
            # As of version 1.21.0, "brightness" is no longer used
            # in Ramona Optics hardware
            # ALl boards that I have in my possension have been updated.
            # The command color changed in version 0.14 such that
            # each color would be multiplied by the value of brightness
            # Therefore, we ensure that the brightness on the chip is set to
            # max
            # In fact more normalization is done, but we patch it away
            # https://github.com/zfphil/illuminate/pull/18
            self.ask('sb.max')

        if self._precision is None:
            self._precision = self._interface_bit_depth

        if self._precision == 'float':
            self._scale_factor = ((1 << self._interface_bit_depth) - 1)
        else:
            if self._precision > self._interface_bit_depth:
                self.close()
                raise ValueError(
                    f"Selected precision {self._precision} is not supported "
                    "by this LED board. "
                    "This board only supports bit depths up to "
                    f"{self._interface_bit_depth} bits."
                    "Please contact support for more assistance.")
            else:
                self._scale_factor = (
                    ((1 << self._interface_bit_depth) - 1) /
                    ((1 << self._precision) - 1)
                )

        # Set the brightness low so we can live
        if self._precision == 'float':
            self.color = self.color_minimum_increment
        else:
            self.color = 1

    def __del__(self):
        self.close()

    def close(self) -> None:
        """Force close the serial port."""
        if self.serial is not None and self.serial.isOpen():
            try:
                self.clear()
                self.serial.flush()
            except SerialException:
                # Ignore any Serial Exceptions that may arise due to
                # a user prematurely removing the USB connection before the
                # device is closed.
                pass
            self.serial.close()

        self._lock_release()

    @staticmethod
    def _make_lock(
            serial_number, group='dialout', chmod=0o666) -> MultiUserFileLock:
        # 0o666 is chosen because that is the default permission set
        # by most people installing the teensy by default
        # https://www.pjrc.com/teensy/loader_linux.html
        # Check the udev rules file
        unique_pyilluminate_locktxt = locks_dir / f"{serial_number}.lock"
        # lock will only be called if the device is closed
        # (when isOpen is called).
        return MultiUserFileLock(unique_pyilluminate_locktxt,
                                 group=group, chmod=chmod,
                                 timeout=0.001)

    def _lock_acquire(self) -> None:
        if not self._use_lock:
            # If the use isn't requesting to use a lock, simply return
            # immediately
            return
        lock = self._make_lock(self.serial_number)
        try:
            lock.acquire()
        except Timeout:
            raise RuntimeError(
                "This pyilluminate board has been opened already. "
                "Establish a new connection by closing this board."
            )

        # Only assign the new lock object after it has been acquired.
        self._lock = lock

    def _lock_release(self) -> None:
        # During garbage collection, the serial
        # device might have been closed first
        # Make sure we cleanup the lock in either case
        if self._lock is not None:
            self._lock.release()
            self._lock = None

    def write(self, data) -> None:
        """Write data to the port.

        If it is a string, encode it as 'utf-8'.
        """
        if self.serial is None:
            raise RuntimeError("__init__ must be successfully called first")
        if isinstance(data, str):
            data = (data + '\n').encode('utf-8')
        self.serial.write(data)

    def read(self, size: int=10000) -> bytearray:
        """Read data from the serial port.

        Returns
        -------
        data: bytearray
            bytearray of data read.

        """
        if self.serial is None:
            raise RuntimeError("__init__ must be successfully called first")
        return self.serial.read(size)

    def readline(self) -> str:
        """Call underlying readline and decode as utf-8."""
        if self.serial is None:
            raise RuntimeError("__init__ must be successfully called first")
        b = self.serial.readline()
        return b.decode('utf-8')

    def read_paragraph(self, raw=False) -> List[str]:
        """Read a whole paragraph of text.

        Returns
        -------
        lines: list
            A list of the lines in the paragraph.

        """
        paragraph = []
        while True:
            line = self.readline()
            if not line:
                raise RuntimeError("Timeout reading from serial")
            line_stripped = line.strip()

            line_clean = line_stripped.strip('-= ')
            if raw:
                paragraph.append(line)
            elif line_clean:
                paragraph.append(line_clean)

            # Ok, so I don't know his exact end of paragraph string.
            # it might be ' -==- \n', but there are inconsistencies with
            # \r\n in Arduino, and probably in his code.
            # This seems safer for now.
            if '-==-' in line_stripped:
                return paragraph

    def ask(self, data: str) -> Union[int, float, None]:
        """Send data, read the output, check for error, extract a number."""
        p = self._ask_list(data)
        self._check_output(p)
        return self._extract_number(p)

    def _check_output(self, p) -> None:
        """Check for errors."""
        # Some commands just return -==-
        # If the data is stripped, this would be an empty list
        if not p:
            return None

        # Error or ERROR are typically returned on error
        # on the first string
        if 'ERROR' in p[0].upper():
            raise RuntimeError('\n'.join(p))

        # Somtimes there is a string that has 'not implemented yet'
        # inside of it
        elif 'not implemented yet' in p[0]:
            raise NotImplementedError('\n'.join(p))

        else:
            return None

    def _extract_number(self, p):
        """Return the float or int located at the end of the list of string."""
        # I don't know how to do mypy for this one!!!
        if not p:
            return None
        # Often, if something is returned, it will be a number
        # so we need to extract it from his list
        # Get the last number from the last string
        number = re.search(r'[-+]?\d*\.?\d?$', p[-1]).group(0)
        if number:
            if '.' in number:
                return float(number)
            else:
                return int(number)
        else:
            return None

    def _ask_list(self, data: str, raw: bool=False) -> List[str]:
        """Read data, return as list of strings."""
        self.write(data)
        return self.read_paragraph(raw)

    def _ask_string(self, data: str, raw: bool =False) -> str:
        """Read data, return as a single string."""
        p = self._ask_list(data, raw)
        if p:
            if raw:
                return ''.join(p)
            else:
                return '\n'.join(p)
        else:
            return ''

    @property
    def led_current_amps(self):
        """Maximum current in amps per LED channel."""
        return 0.02

    @property
    def mac_address(self) -> str:
        """MAC Address of the Teansy that drives the LED board."""
        return self._mac_address

    @property
    def help(self) -> str:
        """Display help information from the illuminate board."""
        if self._help is None:
            # Cache the help string
            # Simply print the raw information the way Zack has it formatted.
            self._help = self._ask_string('?', raw=True)
        return self._help

    @property
    def about(self) -> str:
        """Display information about this LED Array."""
        # Print the resulting string. Strip away all the superfluous chars
        return self._ask_string('about')

    def reboot(self):
        """Run setup routine again, for resetting LED array."""
        # This just returns nothing important
        self.ask('reboot')

    @property
    def version(self) -> str:
        """Display controller version number."""
        # returns version number, probably not a decimal number, so
        # read it as a string
        return self._ask_string('version')

    @property
    def autoclear(self) -> bool:
        """Toggle clearing of array between led updates.

        Returns
        -------
        value: bool
            The current setting of autoclear
        """
        # The autoclear command from the teensy toggles the
        # autoclear bit, so we must remember the state of autoclear
        # in python, and just return the cached value
        return self._autoclear

    @autoclear.setter
    def autoclear(self, value: bool=None) -> None:
        # The autoclear command from the teensy toggles the
        # autoclear bit, so we must remember the state of autoclear
        # in python, and just return the cached value
        if value:
            self._ask_string('ac.1')
            self._autoclear = True
        else:
            self._ask_string('ac.0')
            self._autoclear = False

    @property
    def autoupdate(self) -> bool:
        """Toggle updating of array between led commands.

        Returns
        -------
        value: bool
            The current setting of autoupdate
        """
        # The autoupdate command from the teensy toggles the
        # autoupdate bit, so we must remember the state of autoupdate
        # in python, and just return the cached value
        return self._autoupdate

    @autoupdate.setter
    def autoupdate(self, value: bool=None) -> None:
        # The autoupdate command from the teensy toggles the
        # autoupdate bit, so we must remember the state of autoupdate
        # in python, and just return the cached value
        if value:
            if self._has_autoupdate:
                self._ask_string('au.1')
            self._autoupdate = True
        else:
            if not self._has_autoupdate:
                # Only raise an error when autoUpdate is being set to false
                raise ValueError(
                    "This version of the LED Driver doesn't support "
                    "autoUpdate. Contact support for more information.")
            self._ask_string('au.0')
            self._autoupdate = False

    @property
    def NA(self) -> float:
        """Numerical aperture for bf / df / dpc / cdpc patterns."""
        return self._NA

    @NA.setter
    def NA(self, value: float) -> None:
        self.ask(f'na.{value*100:.0f}')
        self._NA = round(value, 2)

    @property
    def brightness(self) -> float:
        color = self.color
        if ((color[0] == color[1]) and
                (color[0] == color[2])):
            return color[0]
        else:
            raise ValueError('The RGB values are not equal. To access their '
                             'value, use the `color` property instead.')

    @brightness.setter
    def brightness(self, b: float):
        self.color = (b,) * 3

    @property
    def color(self) -> Tuple[float, ...]:
        """LED array color.

        Returns a tuple for the ``(red, green, blue)`` value of the LEDs.

        Returns
        =======
        red
            Integer value for the brightness of the red pixel.
        green
            Integer value for the brightness of the green pixel.
        blue
            Integer value for the blue pixels.
        """
        user_color = tuple(float(i / self._scale_factor) for i in self._color)
        return user_color

    @color.setter
    def color(self, c: Union[float, Iterable[float]]):
        if not isinstance(c, collections.abc.Iterable):
            # Make it a 3 tuple
            c = (c, c, c)

        # Downcast to int for safety
        max_color_int = (1 << self._interface_bit_depth) - 1
        c = tuple(int(i * self._scale_factor) for i in c)

        # Clips color channel to approximately 255 if user input exceeds that
        if any(i > max_color_int for i in c):
            c = tuple(min(i, max_color_int) for i in c)
            user_color = tuple(float(i / self._scale_factor) for i in c)
            warn(f"Maximum color ({self.color_maximum_value})"
                 " exceeded. Requested color clipped to"
                 f" {user_color}", stacklevel=2)

        self.ask(f'sc.{c[0]}.{c[1]}.{c[2]}')
        # Cache the color for future use
        self._color = c
        # man, mypy is annoying.... i can't get typing for this one to work

    # for our friends that speak The Queen's English
    @property
    def colour(self) -> None:
        raise AttributeError(
            "The ``colour`` attribute doesn't exist. Did you mean ``color``?"
        )

    @colour.setter
    def colour(self, c: Union[float, Iterable[float]]) -> None:
        raise AttributeError(
            "The ``colour`` attribute doesn't exist. Did you mean ``color``?"
        )

    @property
    def maximum_current(self):
        return self._maximum_current

    @maximum_current.setter
    def maximum_current(self, value):
        value = int(round(value))
        self.ask('setMaxCurrent.' + f"{value:d}")
        # Cache the value so that firmwares with version less
        # than 1.20.6 can read it back in python.
        # Prior version 1.20.6, we can only set, but not get the value.
        self._maximum_current = value

    @property
    def color_maximum_value(self):
        """Maximum color intensity that can provided to the LED board."""
        return ((1 << self._interface_bit_depth) - 1) / self._scale_factor

    @property
    def color_minimum_increment(self):
        """Minium intensity increment that can be provided to the LED board."""
        if self._precision == 'float':
            return 1 / ((1 << self._interface_bit_depth) - 1)
        else:
            return 1 / self._scale_factor

    @property
    def array_distance(self) -> float:
        """LED array distance in meters."""
        return self._array_distance

    @array_distance.setter
    def array_distance(self, distance: float):
        # sad, [100 * dist(mm) - -or-- 1000 * dist(cm)]
        self.ask('sad.' + f'{distance*1000*100:.0f}')
        self._array_distance = distance

    @property
    def led(self) -> List[int]:
        """Turn on list of LEDs.

        Note that the LEDs along the edges do not
        have all the colors. Therefore, it might be
        deceiving if you set the color to red, then
        call
        ```
        Illuminate.led = 0
        ```
        which makes it seem like it turned off the
        LEDs, but in fact, it simply set LED #0 to
        the color red, which for that particular LED
        doesn't exist.
        """
        return self._led

    @led.setter
    def led(self, led: Union[int, Iterable[int]]) -> None:
        self.turn_on_led(led)

    @property
    def leds(self) -> None:
        raise AttributeError(
            "The ``leds`` attribute doesn't exist. Did you mean ``led``")

    @leds.setter
    def leds(self, value) -> None:
        raise AttributeError(
            "The ``leds`` attribute doesn't exist. Did you mean ``led``")

    def turn_on_led(self, leds: Union[int, Iterable[int]]) -> None:
        """Turn on a single LED(or multiple LEDs in an iterable).


        Parameters
        ----------
        leds: single item or list-like
            If this is single item, then the single LED is turned on.
            If this is an iterable, such as a list, tuple, or numpy array,
            turn on all the LEDs listed in the iterable. ND numpy arrays are
            first converted to 1D numpy arrays, then to a list.

        """
        if isinstance(leds, np.ndarray):
            # As 1D
            leds = leds.reshape(-1).tolist()

        if not leds:
            if self.autoclear:
                self.clear()
            return

        # make leds a list
        if isinstance(leds, collections.abc.Iterable):
            leds = list(leds)
        else:
            # Make a singleton a list
            leds = [leds]

        cmd = 'l.' + '.'.join((str(led) for led in leds))
        # SYNTAX:
        # l.[led  # ].[led #], ...
        # This will raise an error on bad syntax
        if len(cmd) < MAX_ARGUMENT_CHAR_COUNT:
            self.ask(cmd)
        else:
            # Need to breakup the command
            # otherwise serial transmission might fail
            # Mark noticed that one attempts to send more than 64 bytes of
            # data at a time, data gets "lost"
            # This seems to be a buffer issue in the teensy.
            chars_per_led = 1 + len(str(max(leds)))
            max_leds_per_command = (
                MAX_ARGUMENT_CHAR_COUNT - 2) // chars_per_led
            command_chunks = (
                len(leds) + max_leds_per_command - 1) // max_leds_per_command

            old_autoclear = self.autoclear
            old_autoupdate = self.autoupdate
            # if autoupdate isn't found, then gracefully set the LEDs
            # sequentially, even if it blinks for the user
            if self._has_autoupdate:
                self.autoupdate = False
            for i in range(command_chunks):
                these_leds = leds[
                    i * max_leds_per_command:(i + 1) * max_leds_per_command]
                cmd = 'l.' + '.'.join(str(led) for led in these_leds)
                self.ask(cmd)
                if i == 0:
                    self.autoclear = False
            self.autoclear = old_autoclear
            self.autoupdate = old_autoupdate
            if self._has_autoupdate and old_autoupdate:
                self.update()
        self._led = leds

    @property
    def _led(self):
        return self._led_cache

    @_led.setter
    def _led(self, value):
        self._update_led_state(value)

    def _update_led_state(self, led, force_clear=False):
        # The LED state might not exist if the system hasn't booted up
        # Therefore, skip any errors that may occur on "Unefined variable"
        # self._led_state
        if self._led_state is None:
            return
        # Certain functions, like special patterns, or fill array
        # Will clear the LEDs regardless of the `autoclear` functionality
        # THerefore,allow them to add the force clear parameter
        color = np.asarray(self.color)
        if force_clear or self.autoclear:
            self._led_state.data[...] = 0
            led_cache = led
        else:
            led_cache = list(set(self._led_cache).union(led))
        self._led_state.data[led] = color
        self._led_cache = led_cache

    def clear(self) -> None:
        """Clear the LED array."""
        self.ask('x')
        self._update_led_state([], force_clear=True)

    def update(self) -> None:
        """Update the LED array."""
        if not self._has_autoupdate:
            raise NotImplementedError(
                "This command requires an updated version of the firmware. "
                "Contact support for help.")
        self.ask('u')

    def fill_array(self) -> None:
        """Fill the LED array with default color."""
        self.ask('ff')
        self._update_led_state(list(range(self._led_count)), force_clear=True)

    def brightfield(self) -> None:
        """Display brightfield pattern."""
        self.ask('bf')

    def darkfield(self) -> None:
        """Display darkfield pattern."""
        self.ask('df')

    def half_circle(self, pattern: str) -> None:
        """Illuminate half circle(DPC) pattern.

        Parameters
        ----------
        pattern: should be 'top', 'bottom', 'left' or 'right'

        """
        self.ask('dpc.' + pattern)

    def half_circle_color(self, red: int, green: int, blue: int) -> None:
        """Illuminate color DPC pattern."""
        # TODO: should this be a property?
        self.ask(f'cdpc.{red}.{green}.{blue}')

    def annulus(self, minNA: float, maxNA: float) -> None:
        """Display annulus pattern set by min/max NA."""
        # an.[minNA * 100].[maxNA * 100]
        self.ask(f"an.{minNA*100:.0f}.{maxNA*100:.0f}")

    def half_annulus(self, pattern: str, minNA: float, maxNA: float) -> None:
        """Illuminate half annulus."""
        # Find out what the types are
        self.ask(f"ha.{type}.{minNA*100:.0f}.{maxNA*100:.0f}")

    def draw_quadrant(self, red: int, green: int, blue: int) -> None:
        """Draws single quadrant."""
        self.ask(f'dq.{red}.{green}.{blue}')

    def illuminate_uv(self, number: int) -> None:
        """Illuminate UV LED."""
        raise NotImplementedError('Never tested')
        self.ask(f'uv.{number}')

    def _scan(self, command: str, delay: Optional[float]):
        """Send generic scan command.

        These scan commands seem to just timeout on the COM port.

        I kinda want to raise an error on a timeout.
        Right now, it seems to be OK since eventually, it will return -= =-
        but who knows.

        """
        cmd = 'sc' + command

        # See this issue about the comma vs period
        # https://github.com/zfphil/illuminate/issues/7
        if delay is None:
            self.ask(cmd)
        else:
            self.ask(cmd + '.' + f"{delay * 1000:.0f}")

    def scan_full(self, delay: Optional[float]=None) -> None:
        """Scan all active LEDs.

        Sends trigger pulse in between images.

        Delay in seconds.

        Outputs LED list to serial terminal.
        """
        self._scan('f', delay)

    def scan_brightfield(self, delay: Optional[float]=None) -> None:
        """Scan all brightfield LEDs.

        Sends trigger pulse in between images.

        Outputs LED list to serial terminal.
        """
        raise NotImplementedError("Never tested")
        self._scan('b', delay)

    @property
    def sequence_length(self) -> int:
        """Sequence length in terms of independent patterns."""
        return self._sequence_length

    @sequence_length.setter
    def sequence_length(self, length: int):
        self.ask('ssl.' + str(length))
        self._sequence_length = length

    @property
    def sequence(self) -> List[int]:
        """LED sequence value.

        The sequence should be a list of LEDs with their LED number.
        """
        return self._sequence

    @sequence.setter
    def sequence(self, LED_sequence: List[int]) -> None:
        self.ask('ssv.' + '.'.join([str(led) for led in LED_sequence]))
        self._sequence = LED_sequence

    def run_sequence(self, delay: float, trigger_modes: List[float]) -> None:
        """Run sequence with specified delay between each update.

        If update speed is too fast, a: (is shown on the LED array.
        """

        # SYNTAX:
        # rseq.[Delay between each pattern in ms].
        #      [trigger mode  index 0].[index 1].[index 2]
        raise NotImplementedError('Never tested')
        cmd = ('rseq.' + f'{delay * 1000:.0f}' + '.' +
               '.'.join([f'{mode:.0f}' for mode in trigger_modes]))
        self.ask(cmd)

    def run_sequence_fast(self, delay, trigger_modes):
        """Not implemented yet."""
        """
        Badly documented. Make sure to look at the code.

        -----------------------------------
        COMMAND:
        rseqf / runSequenceFast
        SYNTAX:
        rseqf.[Delay between each pattern in ms].[trigger mode for index 0].
             [trigger mode for index 1].[trigger mode for index 2]
        DESCRIPTION:
        Runs sequence with specified delay between each update.
        Uses parallel digital IO to acheive very fast speeds. Only
        available on certain LED arrays.
        -----------------------------------
        """
        raise NotImplementedError('Never tested')

    def print_sequence(self) -> str:
        """Print sequence values to the terminal.

        Returns
        -------
        s: string
            Human readable

        """
        return self._ask_string('pseq')

    def print_sequence_length(self):
        """Print sequence length to the terminal."""
        return self.ask('pseql')

    def step_sequence(self, trigger_start, trigger_update):
        """Trigger sequence.

        Triggers represents the trigger output from each trigger pin on the
        teensy. The modes can be:

        0: No triggering
        1: Trigger at start of frame
        2: Trigger each update of pattern
        """
        cmd = 'sseq'
        cmd = cmd + '.' + ('1' if trigger_start else '0')
        cmd = cmd + '.' + ('1' if trigger_update else '0')
        return self.ask(cmd)

    def reset_sequence(self):
        """Reset sequence index to start."""
        return self.ask('reseq')

    @property
    def sequence_bit_depth(self):
        """Set bit depth of sequence values: 1, 8, [or 16?]."""
        return self._sequence_bit_depth

    @sequence_bit_depth.setter
    def sequence_bit_depth(self, bitdepth):

        # TODO: Don't do value checking upstream fixes
        # https://github.com/zfphil/illuminate/issues/5
        if bitdepth not in [1, 8]:
            raise ValueError("Needs to be 1 or 8")

        self.ask('ssbd.' + str(bitdepth))
        self._sequence_bit_depth = bitdepth

    def find_max_brightness(self, num_leds, color_ratio=None):
        """Calculate the maximum brightness for each color channel of an LED
        that won't exceed the TLC's internal current limit.

        Parameters
        ----------
        num_leds: int
            The number of LEDs to be illuminated.
        color_ratio: (float, float, float)
            The required ratio for the brightness values
            of each color channel (r, g, b)

        Returns
        -------
        brightness: (float, float, float)
            The maximum scaled brightness for each color channel.
        """
        uint16_max = 65535

        if color_ratio is None:
            color_ratio = self.color
        color_ratio = np.asarray(color_ratio)
        color_ratio = color_ratio / np.sum(color_ratio)

        # equation modified from TLC5955 driver
        total_brightness = (self.maximum_current * uint16_max /
                            (num_leds * self._scale_factor *
                             self.led_current_amps))

        max_brightness = total_brightness * color_ratio

        max_one_led_brightness = np.max(max_brightness)
        if max_one_led_brightness > 255:
            max_brightness = max_brightness * 255 / max_one_led_brightness
        return tuple(max_brightness)

    def trigger(self, index):
        """Output TTL trigger pulse to camera."""
        raise NotImplementedError("Never tested")
        return self.ask('tr.' + str(index))

    def trigger_setup(self, index, pin_index, delay):
        """Set up hardware(TTL) triggering."""
        """
        SYNTAX:
        trs.[trigger index].[trigger pin index].
            ['trigger delay between H and L pulses]
        """
        raise NotImplementedError("I haven't implemented this yet")

    def trigger_print(self):
        """Print information about the current i / o trigger setting.

        Returns
        -------
        s: string
            Human readable string describing the trigger.

        """
        return self._ask_string('ptr')

    def trigger_test(self, index):
        """Wait for trigger pulses on the defined channel."""
        raise NotImplementedError("I haven't implemented this yet")
        return self.write('trt.' + str(index))

    def draw_channel(self, led):
        """Draw LED by hardware channel(use for debugging)."""
        raise NotImplementedError("Never tested")
        return self.ask('dc.' + str(led))

    def debug(self, value=None):
        """Set a debug flag. Toggles if value is None."""
        raise NotImplementedError(
            "I have no clue what he does when things are debugging.")

        """
        The debugging flags seem to be a 4 digit number, were each digit of
        the number is assigned to an internal debugging register.

        I also doesn't seem to get reset by the "reboot" command.

        But honestly, after this, all the reading and writing commands
        will probably not work.
        """
        if value is None:
            return self.write('dbg')
        elif value:
            return self.write('dbg.1')
        else:
            return self.write('dbg.0')

    def set_pin_order(self, red_pin, green_pin, blue_pin, led=None):
        """Set pin order(R / G / B) for setup purposes."""
        # Big hack, the LED class basically does what we want,
        # Even though these are pins and not RGB values
        if led is not None:
            cmd = 'spo.' + '.'.join([led, red_pin, green_pin, blue_pin])
        else:
            cmd = 'spo.' + '.'.join([red_pin, green_pin, blue_pin])
        raise NotImplementedError("Never tested")
        return self.write(cmd)

    def delay(self, t):
        """Simply puts the device in a loop for the amount of time in seconds.

        Prints newline approximately 100 ms.

        Returns:
            None

        """
        return self.ask('delay.' + f'{t*1000:.0f}')

    def print_values(self):
        """Print LED value for software interface."""
        raise NotImplementedError('Never tested')
        return self._ask_string('pvals')

    @property
    def parameters_json(self):
        """Print system parameters in a json file.

        NA, LED Array z - distance, etc.
        """
        return self._ask_string('pp')

    @property
    def led_positions(self) -> xr.DataArray:
        """Position of each LED in cartesian coordinates[mm]."""
        if self._led_positions is None:
            self._read_led_positions()

        return self._led_positions

    @property
    def led_state(self) -> xr.DataArray:
        """Current state of the Illuminate LEDs in RGB as a DataArray."""
        return self._led_state

    def positions_as_xarray(self):
        """Return the position of the led information as an xarray.DataArray.

        Returns
        -------
        led_position: xr.DataArray
            This dataarray contains a Nx3 matrix that has rows with the
            ``z, y, x`` coordinates of the leds.
        """
        warn("The positons_as_xarray function has been Deprecated and will be "
             "removed in a future version. Use the led_positions attribute "
             "directly.")
        return self.led_positions

    @property
    def led_positions_NA(self):
        """Print the position of each LED in NA coordinates.

        Not working: See[PR  # 8](https://github.com/zfphil/illuminate/pull/8)
        """
        # I don't use this (yet), so a pull request is welcome for this
        j = json.loads(self._ask_string('pledposna'))
        return j['led_position_list_na']

    def discoparty_demo(self, n_leds=1, time=10):
        """Run a demo routine to show what the array can do.

        Parameters
        ----------
        n_led:
            Number of LEDs to turn on at once

        time:
            The amount of time to run the paterns in seconds

        """
        self.write('disco.' + str(n_leds))
        self._finish_demo(time)

    def demo(self, time: float=10) -> None:
        """Run a demo routine to show what the array can do.

        Ok, I don't know what that blinking is doing, when it is blinking, it
        won't respond to serial commands. Therefore, if you try to wake it up
        while it is blinking, it simply will ignore you

        SEems to blink for a while before starting. Maybe it is turning on
        some UV leds on my board? So this demo's default time is set to 20
        instead.
        """
        if self.serial is None:
            raise RuntimeError("__init__ must be successfully called first")
        self.write('demo')
        previous_timeout = self.serial.timeout
        self.serial.timeout = 6  # Seems to blink for around 5 seconds
        try:
            self._finish_demo(time)
        except Exception as inst:
            self.serial.timeout = previous_timeout
            raise inst
        self.serial.timeout = previous_timeout

    def water_drop_demo(self, time: float=10) -> None:
        """Water drop demo."""
        # Basically, if you let this one go on, and it actually returns
        # not implemented yet, then your read/write requests will always be
        # off by 1
        self.write('water')
        self._finish_demo(time)

    def _finish_demo(self, time: float) -> None:
        if self.serial is None:
            raise RuntimeError("__init__ must be successfully called first")
        sleep(self.serial.timeout)

        # If something is waiting so soon, then it is probably an error
        if self.serial.in_waiting:
            p = self.read_paragraph()
            self._check_output(p)
            return

        sleep(max(time - self.serial.timeout, 0))
        self.ask('')
