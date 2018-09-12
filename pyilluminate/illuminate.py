import json
import re
from time import sleep
from warnings import warn

import numpy as np
from serial import Serial


"""
Trigger notes from Zack's code.

Triggers represents the trigger output from each trigger pin on the teensy.
The modes can be:
0 : No triggering
1 : Trigger at start of frame
2 : Trigger each update of pattern

"""


# @dataclass  # python 3.7 only
class LEDColor:
    """Generic class for representing colors."""

    def __init__(self, *, red: int=0, green: int=0, blue: int=0,
                 brightness: int=None):
        """Specify the RGB color of the LEDColor."""
        if brightness is None:
            self.red = red
            self.green = green
            self.blue = blue
        else:
            self.red = brightness
            self.green = brightness
            self.blue = brightness

    def __str__(self):
        """Print as 'red.green.blue'."""
        cmd = [str(part) for part in self]
        return '.'.join(cmd)

    def __iter__(self):
        for i in self.red, self.green, self.blue:
            yield i


class LED:
    """Generic LED class for setting patterns."""

    def __init__(self, *, led: int=None, red: int=0,
                 green: int=0, blue: int=0):
        """Specify the LED number and the RGB color."""
        self.led = led
        self.red = red
        self.green = green
        self.blue = blue

    def __str__(self):
        """Print as "led.red.green.blue"."""
        if self.led is None:
            cmd = [self.red, self.green, self.blue]
        else:
            cmd = [self.led, self.red, self.green, self.blue]

        cmd = [str(part) for part in cmd]
        return '.'.join(cmd)


class Illuminate:
    """Controlls a SciMicroscopy Illuminate board."""

    @staticmethod
    def find(VID=0x16C0, PID=0x0483):
        """Find all the com ports that are associated with Illuminate.

        Parameters
        ----------
        VID: int
            Expected vendor ID. Teansy 3.1 0x160C

        PID: int
            Expected product ID. Teansy 3.1 0x0483.
        """

        from serial.tools.list_ports import comports
        com = comports()
        devices = []
        for c in com:
            if c.vid == VID and c.pid == PID:
                devices.append(c.device)
        return devices

    def __init__(self, *, port=None, reboot_on_start=True,
                 baudrate=115200, timeout=0.500, open_device=True):
        """Open the Illumination board."""
        if timeout < 0.4:
            warn('Timeout too small, try providing at least 0.5 seconds.')

        self.reboot_on_start = reboot_on_start
        self.serial = Serial(port=None,
                             baudrate=baudrate, timeout=timeout)
        if port is not None:
            self.serial.port = port
        if open_device:
            self.open()

    def _load_parameters(self):
        """Read the parameters from the illuminate board.

        Function is called automatically when the device is opened.
        """
        parameters = json.loads(self.parameters_json)
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
        p = json.loads(self._ask_string('pledpos'))[
            'led_position_list_cartesian']
        self.N_leds = len(p)
        self._led_positions = np.empty(self.N_leds, dtype=[('x', float),
                                                           ('y', float),
                                                           ('z', float)])

        for key, item in p.items():
            # x, y units in mm
            # z unitz in cm
            self._led_positions[int(key)]['x'] = item[0] * 0.001
            self._led_positions[int(key)]['y'] = item[1] * 0.001
            self._led_positions[int(key)]['z'] = item[2] * 0.01

    @property
    def led_count(self):
        return self._led_count

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def open(self):
        """Open the serial port. Only useful if you closed it."""
        if not self.serial.isOpen():
            if self.serial.port is None:
                self.serial.port = Illuminate.find()[0]
            self.serial.open()
        self.serial.reset_output_buffer()
        self.serial.reset_input_buffer()
        self.serial.flush()
        if self.reboot_on_start:
            self.reboot()
        self._load_parameters()
        # Set the brightness low so we can live
        self.brightness = 1

    def __del__(self):
        self.close()

    def close(self):
        """Force close the serial port."""
        if self.serial.isOpen():
            self.clear()
            self.serial.close()

    def write(self, data):
        """Write data to the port.

        If it is a string, encode it as 'utf-8'.
        """
        if isinstance(data, str):
            data = (data + '\n').encode('utf-8')
        self.serial.write(data)

    def read(self, size=10000):
        """Read data from the serial port.

        Returns
        -------
        data: bytearray
            bytearray of data read.

        """
        return self.serial.read(size)

    def readline(self):
        """Call underlying readline and decode as utf-8."""
        b = self.serial.readline()
        return b.decode('utf-8')

    def read_paragraph(self, raw=False):
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

    def ask(self, data):
        """Send data, read the output, check for error, extract a number."""
        p = self._ask_list(data)
        self._check_output(p)
        return self._extract_number(p)

    def _check_output(self, p):
        """Check for errors."""
        # Some commands just return -==-
        # If the data is stripped, this would be an empty list
        if not p:
            return

        # Error or ERROR are typically returned on error
        # on the first string
        if 'ERROR' in p[0].upper():
            raise RuntimeError('\n'.join(p))

        # Somtimes there is a string that has 'not implemented yet'
        # inside of it
        elif 'not implemented yet' in p[0]:
            raise NotImplementedError('\n'.join(p))

    def _extract_number(self, p):
        """Return the float or int located at the end of the list of string."""
        if not p:
            return
        # Often, if something is returned, it will be a number
        # so we need to extract it from his list
        # Get the last number from the last string
        number = re.search(r'[-+]?\d*\.?\d?$', p[-1]).group(0)
        if number:
            if '.' in number:
                return float(number)
            else:
                return int(number)

    def _ask_list(self, data, raw=False):
        """Read data, return as list of strings."""
        self.write(data)
        return self.read_paragraph(raw)

    def _ask_string(self, data, raw=False):
        """Read data, return as a single string."""
        p = self._ask_list(data, raw)
        if p:
            if raw:
                return ''.join(p)
            else:
                return '\n'.join(p)

    @property
    def mac_address(self):
        """MAC Address of the Teansy that drives the LED board."""
        return self._mac_address

    @property
    def help(self):
        """Display help information."""
        # Simply print the raw information the way Zack has it formatted.
        return self._ask_string('?', raw=True)

    @property
    def about(self):
        """Display information about this LED Array."""
        # Print the resulting string. Strip away all the superfluous chars
        return self._ask_string('about')

    def reboot(self):
        """Run setup routine again, for resetting LED array."""
        # This just returns nothing important
        return self.ask('reboot')

    @property
    def version(self):
        """Display controller version number."""
        # returns version number, probably not a decimal number, so
        # read it as a string
        return self._ask_string('version')

    def autoclear(self, value=None):
        """Toggle clearing of array between led updates.

        Can call with or without options.

        Parameters
        ----------
        value: bool
            If set to `True`, the LED array will clear before and after each
            new command. If set to `False`, False: LED array will NOT clear
            before and after each new command.

        Returns
        -------
        value: bool
            The value of autoclear after the command.
        """
        if value is None:
            s = self._ask_string('ac')
        else:
            if value:
                s = self._ask_string('ac.1')
            else:
                s = self._ask_string('ac.0')

        if int(re.search('\d', s).group(0)):
            return True
        else:
            return False

    @property
    def NA(self):
        """Numerical aperture for bf / df / dpc / cdpc patterns."""
        return self._NA

    @NA.setter
    def NA(self, value):
        self.ask(f'na.{value*100:.0f}')
        self._NA = round(value, 2)

    @property
    def brightness(self):
        if (self._color.red == self._color.blue and
                self._color.red == self._color.green):
            return self._color.red
        else:
            raise ValueError('The RGB values are not equal. To access their '
                             'value, use the `color` property instead.')

    @brightness.setter
    def brightness(self, b):
        self.color = LEDColor(brightness=b)

    @property
    def color(self):
        """LED array color."""
        return self._color

    @color.setter
    def color(self, c):
        # sc, [rgbVal] - -or-- sc.[rVal].[gVal].[bVal]
        self.ask('sc.' + str(c))
        self._color = c

    @property
    def array_distance(self):
        """LED array distance in meters."""
        return self._array_distance

    @array_distance.setter
    def array_distance(self, distance):
        # sad, [100 * dist(mm) - -or-- 1000 * dist(cm)]
        self.ask('sad.' + f'{distance*1000*100:.0f}')
        self._array_distance = distance

    @property
    def led(self):
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
    def led(self, led):
        self.turn_on_led(led)

    def turn_on_led(self, leds):
        """Turn on a single LED(or multiple LEDs in an iterable).


        Parameters
        ----------
        leds: single item or list-like
            If this is single item, then the single LED is turned on.
            If this is an iterable, such as a list, tuple, or numpy array,
            turn on all the LEDs listed in the iterable. ND numpy arrays are
            first converted to 1D numpy arrays, then to a list.

        """
        clear_result = self.clear()
        if leds is None:
            return clear_result

        if isinstance(leds, np.ndarray):
            # As 1D
            leds = leds.reshape(-1).tolist()
        try:
            cmd = '.'.join((str(led) for led in leds))
        except TypeError:
            cmd = str(leds)
            # Make it a tuple
            led = (leds, )
        # SYNTAX:
        # l.[led  # ].[led #], ...
        result = self.ask('l.' + cmd)
        self._led = tuple(led)
        return result

    def clear(self):
        """Clear the LED array."""
        result = self.ask('x')
        self._led = None
        return result

    def fill_array(self):
        """Fill the LED array with default color."""

        self.clear()
        result = self.ask('ff')
        self._led = tuple(range(self._led_count))
        return result

    def brightfield(self):
        """Display brightfield pattern."""
        return self.ask('bf')

    def darkfield(self):
        """Display darkfield pattern."""
        return self.ask('df')

    def half_circle(self, pattern):
        """Illuminate half circle(DPC) pattern.

        Parameters
        ----------
        pattern: should be 'top', 'bottom', 'left' or 'right'

        """
        return self.ask('dpc.' + pattern)

    def half_circle_color(self, red, green, blue):
        """Illuminate color DPC pattern."""
        # TODO: should this be a property?
        return self.ask('cdpc.' +
                        str(LEDColor(red=red, green=green, blue=blue)))

    def annulus(self, minNA, maxNA):
        """Display annulus pattern set by min/max NA."""
        # an.[minNA * 100].[maxNA * 100]
        return self.ask(f"an.{minNA*100:.0f}.{maxNA*100:.0f}")

    def half_annulus(self, pattern, minNA, maxNA):
        """Illuminate half annulus."""
        # Find out what the types are
        return self.ask(f"ha.{type}.{minNA*100:.0f}.{maxNA*100:.0f}")

    def draw_quadrant(self, red, green, blue):
        """Draws single quadrant."""
        return self.ask('dq.' + str(LEDColor(red=red, green=green, blue=blue)))

    def illuminate_uv(self, number):
        """Illuminate UV LED."""
        raise NotImplemented('Never tested')
        return self.ask(f'uv.{number}')

    def _scan(self, command, delay):
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
            return self.ask(cmd)
        else:
            return self.ask(cmd + '.' + f"{delay * 1000:.0f}")

    def scan_full(self, delay=None):
        """Scan all active LEDs.

        Sends trigger pulse in between images.

        Delay in seconds.

        Outputs LED list to serial terminal.
        """
        return self._scan('f', delay)

    def scan_brightfield(self, delay=None):
        """Scan all brightfield LEDs.

        Sends trigger pulse in between images.

        Outputs LED list to serial terminal.
        """
        raise NotImplementedError("Never tested")
        return self._scan('b', delay)

    @property
    def sequence_length(self):
        """Sequence length in terms of independent patterns."""
        return self._sequence_length

    @sequence_length.setter
    def sequence_length(self, length):
        raise NotImplementedError("Never tested")
        r = self.ask('ssl.' + str(length))
        self._sequence_length = length
        return r

    @property
    def sequence(self):
        """LED sequence value.

        The sequence should be a list of LEDs with their LED number.
        """
        return self._sequence

    @sequence.setter
    def sequence(self, LED_sequence):
        raise NotImplemented('Never tested. Wrong SYNTAX')
        r = self.ask('ssv.' + '.'.join([str(l) for l in LED_sequence]))
        self._sequence = LED_sequence
        return r

    def run_sequence(self, delay, trigger_modes):
        """Run sequence with specified delay between each update.

        If update speed is too fast, a: (is shown on the LED array.
        """

        # SYNTAX:
        # rseq.[Delay between each pattern in ms].
        #      [trigger mode  index 0].[index 1].[index 2]
        raise NotImplemented('Never tested')
        cmd = ('rseq.' + f'{delay * 1000:.0f}' + '.' +
               '.'.join([f'{mode:.0f}' for mode in trigger_modes]))
        return self.ask(cmd)

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
        raise NotImplemented('Never tested')

    def print_sequence(self):
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
        raise NotImplemented("I haven't implemented this yet")

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
        raise NotImplemented("I haven't implemented this yet")
        return self.write('trt.' + str(index))

    def draw_channel(self, led):
        """Draw LED by hardware channel(use for debugging)."""
        raise NotImplementedError("Never tested")
        return self.ask('dc.' + str(led))

    def debug(self, value=None):
        """Set a debug flag. Toggles if value is None."""
        raise NotImplemented(
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
        cmd = 'spo.' + str(LED(led=led, red=red_pin,
                               green=green_pin, blue=blue_pin))
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
        raise NotImplemented('Never tested')
        return self._ask_string('pvals')

    @property
    def parameters_json(self):
        """Print system parameters in a json file.

        NA, LED Array z - distance, etc.
        """
        return self._ask_string('pp')

    @property
    def led_positions(self):
        """Position of each LED in cartesian coordinates[mm]."""
        return self._led_positions

    def positions_as_xarray(self):
        import xarray as xr
        positions = np.zeros((len(self.led_positions), 3))
        positions[:, 2] = self.led_positions['x']
        positions[:, 1] = self.led_positions['y']
        positions[:, 0] = self.led_positions['z']
        # The boards have a 1 mm offset in each dimension I think
        positions[:, 1:3] += 0.001

        positions = xr.DataArray(
            positions, dims=['led_number', 'zyx'],
            coords={'led_number': np.arange(len(positions)),
                    'zyx': ['z', 'y', 'x']})

        uv_leds = self.uv_leds

        rgb_or_uv = xr.DataArray(
            np.empty(len(positions), dtype='<U3'),
            dims=['led_number'],
            coords={'led_number': np.arange(len(positions))})
        rgb_or_uv[...] = 'rgb'
        rgb_or_uv[uv_leds] = 'uv'
        # %%
        positions = positions.assign_coords(rgb_or_uv=rgb_or_uv)
        return positions

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

    def demo(self, time=10):
        """Run a demo routine to show what the array can do.

        Ok, I don't know what that blinking is doing, when it is blinking, it
        won't respond to serial commands. Therefore, if you try to wake it up
        while it is blinking, it simply will ignore you

        SEems to blink for a while before starting. Maybe it is turning on
        some UV leds on my board? So this demo's default time is set to 20
        instead.
        """
        self.write('demo')
        previous_timeout = self.serial.timeout
        self.serial.timeout = 6  # Seems to blink for around 5 seconds
        try:
            r = self._finish_demo(time)
        except Exception as inst:
            self.serial.timeout = previous_timeout
            raise inst
        self.serial.timeout = previous_timeout
        return r

    def water_drop_demo(self, time=10):
        """Water drop demo."""
        # Basically, if you let this one go on, and it actually returns
        # not implemented yet, then your read/write requests will always be
        # off by 1
        self.write('water')
        self._finish_demo(time)

    def _finish_demo(self, time):
        sleep(self.serial.timeout)

        # If something is waiting so soon, then it is probably an error
        if self.serial.in_waiting:
            p = self.read_paragraph()
            self._check_output(p)
            return

        sleep(max(time - self.serial.timeout, 0))
        return self.ask('')
