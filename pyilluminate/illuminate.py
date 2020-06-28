import json
import re
from time import sleep
from warnings import warn
from typing import List, Union, Optional, Iterable, Tuple
import collections
from distutils.version import LooseVersion
from dataclasses import dataclass

import xarray as xr

import numpy as np
from serial import Serial, SerialException
from serial.tools.list_ports import comports


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


@dataclass
class LEDColor:
    """Generic class for representing colors."""
    red: int = 0
    green: int = 0
    blue: int = 0
    brightness: Optional[int] = None

    def __init__(self, *, brightness: int=None,
                 red: int=0, green: int=0, blue: int=0):
        warn("The LEDColor Class has been deprecated. "
             "Please use a standard tuple of 3 or List of 3 elements.")
        if brightness is not None:
            red = brightness
            green = brightness
            blue = brightness
        self.brightness = brightness

        self.red = int(red)
        self.green = int(green)
        self.blue = int(blue)

    def __iter__(self):
        return (i for i in (self.red, self.green, self.blue))


class Illuminate:
    """Controlls a SciMicroscopy Illuminate board."""

    VID_PID_s = [
        (0x16C0, 0x0483),
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
                 serial_number: str=None) -> None:
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
        mac_address: string
            Port numbers may change from computer to computer.
            If `mac_address` is provided, then ``find_by_mac_address`` is
            called to find the port associated with the mac address.
            `mac_address` takes precedence over `port`

        """
        self.serial = None
        if timeout < 0.4:
            warn('Timeout too small, try providing at least 0.5 seconds.')

        if mac_address is not None:
            serial_number = self.serial_by_mac_address(mac_address)
            warn(f'The parameter mac_address is deprecated and will be '
                 f'removed in a future version. Use the parameter '
                 f'serial_number instead. The serial number associated '
                 f'with the device with mac_address="{mac_address}" is '
                 f'"{serial_number}".', stacklevel=2)
        if serial_number is not None:
            available_ports = self._device_serial_number_pairs(
                serial_numbers=[serial_number])
            if len(available_ports) == 0:
                raise RuntimeError(
                    f"Could not find serial number: {serial_number}")
            port, found_serial_number = available_ports[0]
            self.serial_number = found_serial_number

        self.reboot_on_start = reboot_on_start
        # Explicitely provide None to the port so as to delay opening
        # the device until the very end of the setup
        self.serial = Serial(port=None,
                             baudrate=baudrate, timeout=timeout)
        # Make the buffer size really large since the LED positions,
        # communicated as a JSON string take quite a few characters to send
        if hasattr(self.serial, 'set_buffer_size'):
            # this doesn't exist on all platforms
            self.serial.set_buffer_size(rx_size=50000)
        if port is not None:
            self.serial.port = port
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
                f"serial number combination.")

    @property
    def device_name(self):
        """The human readable name of the device."""
        return self._device_name

    def _load_parameters(self) -> None:
        """Read the parameters from the illuminate board.

        Function is called automatically when the device is opened.
        """
        p_raw = self.parameters_json
        parameters = json.loads(p_raw)
        self._device_name = parameters['device_name']
        self._part_number = parameters['part_number']
        self._serial_number = parameters['serial_number']
        self._led_count = parameters['led_count']
        # self._center_wavelength
        # self.color_channels
        self._sequence_bit_depth = parameters['bit_depth']
        self._mac_address = parameters['mac_address']

        # There are a ton of default properties that are not easy to read.
        # Maybe I can get Zack to implement reading them, but I'm not sure if
        # that will be possible.

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

        self.N_leds = len(p)

        led_positions = xr.DataArray(
            np.empty((self.N_leds, 3)),
            dims=['led_number', 'zyx'],
            coords={'led_number': np.arange(self.N_leds),
                    'zyx': ['z', 'y', 'x']})
        for key, item in p.items():
            # x, y are provided in units of mm
            # z is provided in units of cm
            key = int(key)
            led_positions[key, 2] = item[0] * 0.001
            led_positions[key, 1] = item[1] * 0.001
            led_positions[key, 0] = item[2] * 0.01

        self._led_positions = led_positions

    @property
    def led_count(self) -> int:
        return self._led_count

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def open(self) -> None:
        """Open the serial port. Only useful if you closed it."""
        if self.serial is None:
            raise RuntimeError("__init__ must be successfully called first")
        if not self.serial.isOpen():
            if self.serial.port is None:
                available_ports = self._device_serial_number_pairs()
                if len(available_ports) == 0:
                    raise RuntimeError("So Illuminate devices found")
                port, serial_number = available_ports[0]
                self.serial.port = port
                self.serial_number = serial_number
            try:
                self.serial.open()
            except SerialException:
                raise SerialException(
                    "Must close previous Illuminate connection before "
                    "establishing a new one. If there is a previous instance "
                    "of Illuminate either delete the object or call the "
                    "'close' method.")
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
            # This reboot procedure will clear the device
            self.reboot()
        try:
            self._load_parameters()
        except json.JSONDecodeError as e:
            self.close()
            e.args = (('Could not successfully open the Illuminate board.',) +
                      e.args)
            raise e
        # Set the brightness low so we can live
        self.brightness = 1
        # Set it to clear between commands.
        # This may have changed due to the user having previously
        # Opened the Illuminate board, so we set it to a safe default
        self.autoclear = True

        if LooseVersion(self.version) > '1.13':
            # ALl boards that I have in my possension have been updated.
            # The command color changed in version 0.14 such that
            # each color would be multiplied by the value of brightness
            # Therefore, we ensure that the brightness on the chip is set to
            # max
            # In fact more normalization is done, but we patch it away
            # https://github.com/zfphil/illuminate/pull/18
            self.ask('sb.max')

    def __del__(self):
        self.close()

    def close(self) -> None:
        """Force close the serial port."""
        if self.serial is not None and self.serial.isOpen():
            self.clear()
            self.serial.flush()
            self.serial.close()

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
    def mac_address(self) -> str:
        """MAC Address of the Teansy that drives the LED board."""
        return self._mac_address

    @property
    def help(self) -> str:
        """Display help information."""
        # Simply print the raw information the way Zack has it formatted.
        return self._ask_string('?', raw=True)

    @property
    def about(self) -> str:
        """Display information about this LED Array."""
        # Print the resulting string. Strip away all the superfluous chars
        return self._ask_string('about')

    def reboot(self):
        """Run setup routine again, for resetting LED array."""
        # This just returns nothing important
        return self.ask('reboot')

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
    def NA(self) -> float:
        """Numerical aperture for bf / df / dpc / cdpc patterns."""
        return self._NA

    @NA.setter
    def NA(self, value: float) -> None:
        self.ask(f'na.{value*100:.0f}')
        self._NA = round(value, 2)

    @property
    def brightness(self) -> int:
        if (self._color[0] == self._color[1] and
                self._color[0] == self._color[2]):
            return self._color[0]
        else:
            raise ValueError('The RGB values are not equal. To access their '
                             'value, use the `color` property instead.')

    @brightness.setter
    def brightness(self, b: int):
        self.color = (b,) * 3

    @property
    def color(self) -> Tuple[int, ...]:
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
        return self._color

    @color.setter
    def color(self, c: Union[int, Iterable[int]]):
        if isinstance(c, LEDColor):
            c = (c.red, c.green, c.blue)
        elif not isinstance(c, collections.abc.Iterable):
            # Make it a 3 tuple
            c = (c,) * 3

        # Downcast to int for safety
        c = tuple(int(i) for i in c)

        self.ask(f'sc.{c[0]}.{c[1]}.{c[2]}')
        # Cache the color for future use
        self._color = c

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
            return None

        # make leds a list
        if isinstance(leds, collections.abc.Iterable):
            leds = list(leds)
        else:
            # Make a singleton a list
            leds = [leds]
        cmd = '.'.join((str(led) for led in leds))
        # SYNTAX:
        # l.[led  # ].[led #], ...
        # This will raise an error on bad syntax
        self.ask('l.' + cmd)
        self._led = leds

    def clear(self) -> None:
        """Clear the LED array."""
        self.ask('x')
        self._led = []

    def fill_array(self) -> None:
        """Fill the LED array with default color."""
        self.ask('ff')
        self._led = list(range(self._led_count))

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
        return self._led_positions

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
