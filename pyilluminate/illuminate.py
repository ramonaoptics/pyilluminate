import re
from warnings import warn
from dataclasses import dataclass
from serial import Serial
from time import sleep


"""
Trigger notes from Zack's code.

Triggers represents the trigger output from each trigger pin on the teensy. The modes can be:
0 : No triggering
1 : Trigger at start of frame
2 : Trigger each update of pattern

"""

@dataclass
class Color:
    """Generic class for representing colors."""

    red: int = 0
    green: int = 0
    blue: int = 0

    def __str__(self):
        """Print as 'red.green.blue'."""
        cmd = [self.red, self.green, self.blue]
        cmd = [str(part) for part in cmd]
        return '.'.join(cmd)

@dataclass
class LED:
    """Generic LED class for setting patterns."""

    led: int = None
    red: int = 0
    green: int = 0
    blue: int = 0

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

    def __init__(self, port,  reboot_on_start=True,
                 baudrate=115200, timeout=0.500):
        """Open the Illumination board."""
        if timeout < 0.4:
            warn('Timeout too small, try providing at least 0.5 seconds.')
        self.serial = Serial(port, baudrate=baudrate, timeout=timeout)

        if reboot_on_start:
            self.reboot()

    def __del__(self):  # noqa
        self.close()

    def open(self):
        """Open the serial port. Only useful if you closed it."""
        self.serial.open()

    def close(self):
        """Force close the serial port."""
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

        Returns:
        bytearray of data

        """
        return self.serial.read(size)

    def readline(self):
        """Call underlying readline and decode as utf-8."""
        b = self.serial.readline()
        return b.decode('utf-8')

    def read_paragraph(self, raw=False):
        """Read a whole paragraph of text.

        Returns:
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
            return '\n'.join(p)

    def help(self):
        """Display help information."""
        # Simply print the raw information the way Zack has it formatted.
        return self._ask_string('?', raw=True)

    def about(self):
        """Display information about this LED Array."""
        # Print the resulting string. Strip away all the superfluous chars
        return self._ask_string('about')

    def reboot(self):
        """Run setup routine again, for resetting LED array."""
        # This just returns nothing important
        return self.ask('reboot')

    def version(self):
        """Display controller version number."""
        # returns version number, probably not a decimal number, so
        # read it as a string
        return self._ask_string('version')

    def autoclear(self, value=None):
        """Toggle clearing of array between led updates.

        Can call with or without options.

        Returns:
            True: LED array will clear before and after each new command
            False: LED array will NOT clear before and after each new command

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
        return self._NA

    @NA.setter
    def set_NA(self, NA):
        """Set na used for bf / df / dpc / cdpc patterns."""
        raise NotImplemented("Never tested")
        r = self.ask(f'na.{NA*100:.0f}')
        self._NA = round(NA, 2)
        return r

    @property
    def color(self):
        return self._color

    @color.setter
    def set_color(self, red, green, blue):
        """Set LED array color"""
        raise NotImplemented('Not tested')
        # sc, [rgbVal] - -or-- sc.[rVal].[gVal].[bVal]
        c = Color(red=red, green=green, blue=blue)
        r = self.ask('sc.' + str(c))
        self._color = c
        return r

    @property
    def array_distance(self):
        return self._array_distance

    @array_distance.setter
    def set_array_distance(self, distance):
        """Set LED array distance."""
        # sad, [100 * dist(mm) - -or-- 1000 * dist(cm)]
        raise NotImplemented('Not tested')
        r = self.ask('sad' + f'{distance*1000*100:.0f}')
        self._array_distance = distance
        return r

    def turn_on_led(self, leds):
        """Turn on a single LED(or multiple LEDs in an iterable).

        SYNTAX:
        l.[led  # ].[led #], ...

        Returns:
            None

        """
        try:
            leds = [str(led) for led in leds]
            leds = '.'.join(leds)
        except TypeError:
            leds = str(leds)

        return self.ask('l.' + leds)

    def clear(self):
        """Clear the LED array.

        Returns:
            None

        """
        return self.ask('x')

    def fill_array(self):
        """Fill the LED array with default color.

        Returns:
            None

        """
        return self.ask('ff')

    def brightfield(self):
        """Display brightfield pattern."""
        raise NotImplementedError("Never tested")
        return self.ask('bf')

    def darkfield(self):
        """Display darkfield pattern."""
        raise NotImplementedError("Never tested")
        return self.ask('df')

    def half_circle(self, pattern):
        """Illuminate half circle(DPC) pattern"""
        # dpc.[t / b / l / r] - -or-- dpc.[top / bottom / left / right]
        raise NotImplemented('Never tested')
        return self.ask('dpc.' + pattern)

    def half_circle_color(self, red, green, blue):
        """Illuminate color DPC pattern."""
        raise NotImplemented('Never tested')
        return self.ask('cdpc.' + str(Color(red=red, green=green, blue=blue)))

    def annulus(self, minNA, maxNA):
        """Display annulus pattern set by min/max NA."""
        raise NotImplemented('Never tested')
        # an.[minNA * 100].[maxNA * 100]
        return self.ask(f"an.{minNA*100:.0f}.{maxNA*100:.0f}")

    def half_annulus(self, pattern, minNA, maxNA):
        """Illuminate half annulus"""
        raise NotImplemented('Never tested')
        # Find out what the types are
        return self.ask(f"ha.{type}.{minNA*100:.0f}.{maxNA*100:.0f}")

    def draw_quadrant(self, red, green, blue):
        """Draws single quadrant."""
        raise NotImplemented('Never tested')
        return self.ask('dq.' + Color(red=red, green=green, blue=blue))

    def illuminate_uv(self, number):
        """Illuminate UV LED."""
        raise NotImplemented('Never tested')
        return self.ask(f'uv.{number}')

    def draw_hole(self, hole):
        """Illuminate LEDs around a single hole.

        Returns:
            None

        """
        return self.ask('drawHole.' + str(hole))

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
        return self._sequence_length

    @sequence_length.setter
    def set_sequence_length(self, length):
        """Set sequence length in terms of independent patterns."""
        raise NotImplementedError("Never tested")
        r = self.ask('ssl,' + str(length))
        self._sequence_length = length
        return r

    @property
    def sequence(self):
        return self._sequence

    @property.setter
    def set_sequence(self, LED_sequence):
        """Set LED sequence value.

        Parameters
        ==========
        LED_sequence: a list of LEDs with their LED number.
        """
        raise NotImplemented('Never tested. Wrong SYNTAX')
        r = self.ask('ssv.' +'.'.join([str(l) for l in LED_sequence]))
        self._sequence = LED_sequence
        return r

    def run_sequence(self, delay, trigger_modes):
        """Runs sequence with specified delay between each update.

        If update speed is too fast, a: (is shown on the LED array.
        SYNTAX:
        rseq, [Delay between each pattern in ms].[trigger mode  index 0].[index 1].[index 2]
        """
        raise NotImplemented('Never tested')
        cmd = ('rseq.' + f'{delay * 1000:.0f}' + '.' +
               '.'.join([f'{mode:.0f}' for mode in trigger_modes]))
        return self.ask(cmd)

    def run_sequence_fast(self, delay, trigger_modes):
        """This seems to be badly documented. Make sure to look at the code.
        -----------------------------------
        COMMAND:
        rseqf / runSequenceFast
        SYNTAX:
        rseqf, [Delay between each pattern in ms].[trigger mode for index 0].[trigger mode for index 1].[trigger mode for index 2]
        DESCRIPTION:
        Runs sequence with specified delay between each update. Uses parallel digital IO to acheive very fast speeds. Only available on certain LED arrays.
        -----------------------------------
        """
        raise NotImplemented('Never tested')

    def print_sequence(self):
        """Print sequence values to the terminal.

        Returns:
            String Human readable

        """
        return self._ask_string('pseq')

    def print_sequence_length(self):
        """Print sequence length to the terminal."""
        return self.ask('pseql')

    def step_sequence(self, trigger_start, trigger_update):
        """
        Triggers represents the trigger output from each trigger pin on the teensy. The modes can be:
        0 : No triggering
        1 : Trigger at start of frame
        2 : Trigger each update of pattern
        """
        cmd = 'sseq'
        cmd = cmd + '.' + ('1' if trigger_start else '0')
        cmd = cmd + '.' + ('1' if trigger_update else '0')
        return self.ask(cmd)

    def reset_sequence(self):
        """Reset sequence index to start.

        Returns:
            None

        """
        return self.ask('reseq')

    @property
    def sequence_bit_depth(self):
        return self._sequence_bit_depth

    @sequence_bit_deth.setter
    def set_sequence_bit_depth(self, bitdepth):
        """Set bit depth of sequence values: 1, 8, [or 16?].

        Returns:
            New bitdepth

        """
        # TODO: Don't do value checking upstream fixes
        # https://github.com/zfphil/illuminate/issues/5
        if bitdepth not in [1, 8]:
            raise ValueError("Needs to be 1 or 8")

        r = self.ask('ssbd.' + str(bitdepth))
        self._sequence_bit_depth = bitdepth
        return r

    def trigger(self, index):
        """Output TTL trigger pulse to camera."""
        raise NotImplementedError("Never tested")
        return self.ask('tr.' + str(index))

    def trigger_setup(self, index, pin_index, delay):
        """Set up hardware(TTL) triggering.

        SYNTAX:
        trs.[trigger index].[trigger pin index].['trigger delay between H and L pulses]
        """
        raise NotImplemented("I haven't implemented this yet")

    def trigger_print(self):
        """Print information about the current i / o trigger setting.

        Returns:
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

    def print_parameters_json(self):
        """Print system parameters in a json file.

        NA, LED Array z - distance, etc.
        """
        raise NotImplemented('Never tested')
        return self._ask_string('pp')

    def print_led_positions(self):
        """Print the positions of each LED in cartesian coordinates."""
        raise NotImplemented('Never tested')
        return self._ask_string('pledpos')

    def print_led_positions_NA(self):
        """Print the position of each LED in NA coordinates.

        Returns
        =======
        NA_x,NA_y,distance
        """
        raise NotImplemented('Never testesd')
        return self._ask_string('pledposna')

    def discoparty_demo(self, n_leds=1, time=10):
        """Run a demo routine to show what the array can do.

        Parameters
        ==========
        n_led: Number of LEDs to turn on at once
        time: The amount of time to run the paterns in seconds

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
        except:
            self.serial.timeout = previous_timeout
            raise
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
