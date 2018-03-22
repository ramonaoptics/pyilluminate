from serial import Serial
from dataclasses import dataclass


@dataclass
class LED:
    led: int = None
    red: int = 0
    green: int = 0
    blue: int = 0

    def __str__(self):
        if self.led is None:
            cmd = [self.red, self.green, self.blue]
        else:
            cmd = [self.led, self.red, self.green, self.blue]

        cmd = [str(part) for part in cmd]
        return cmd.join('.')


class illuminate:
    """Controlls a SciMicroscopy Illuminate board."""

    def __init__(self, port, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self.serial = Serial(port, baudrate=baudrate, timeout=timeout)

    def write(self, data):
        if isinstance(data, str):
            data = (data + '\n').encode('utf-8')
        self.serial.write(data)

    def read(self, size=1):
        return self.serial.read(size)

    def readline(self):
        b = self.serial.readline()
        return b.decode('utf-8')

    def ask(self, data):
        self.write(data)
        return self.readline()

    def help(self):
        """Display help information."""
        return self.ask('?')

    def about(self):
        """Displays information about this LED Array."""
        return self.ask('about')

    def reboot(self):
        """Runs setup routine again, for resetting LED array."""
        return self.ask('reboot')

    def version(self):
        """Display controller version number."""
        return self.ask('version')

    def autoclear(self, value=None):
        """Toggle clearing of array between led updates.

        Can call with or without options.
        """
        if value is None:
            self.write('ac')
        else:
            if value:
                self.write('ac.1')
            else:
                self.write('ac.0')

    """
    COMMAND:
    na / setNa
    SYNTAX:
    na.[na*100]
    DESCRIPTION:
    Set na used for bf/df/dpc/cdpc patterns
    -----------------------------------
    COMMAND:
    sc / setColor
    SYNTAX:
    sc,[rgbVal] --or-- sc.[rVal].[gVal].[bVal]
    DESCRIPTION:
    Set LED array color
    -----------------------------------
    COMMAND:
    sad / setArrayDistance
    SYNTAX:
    sad,[100*dist(mm) --or-- 1000*dist(cm)]
    DESCRIPTION:
    Set LED array distance
    -----------------------------------
    """

    def turn_on_led(self, leds):
        """Turn on a single LED (or multiple LEDs in an iterable).

        SYNTAX:
        l.[led #].[led #], ...
        """
        try:
            leds = [str(led) for led in leds]
            leds = leds.join('.')
        except TypeError:
            leds = str(leds)

        self.send('l.' + leds)

    def clear(self):
        """Clear the LED array."""
        self.write('x')

    def fill_array(self):
        """Fill the LED array with default color."""
        self.write('ff')

    def brightfield(self):
        """Display brightfield pattern"""
        self.write('bf')

    def darkfield(self):
        """Display darkfield pattern."""
        self.write('df')

    """
    COMMAND:
    dpc / halfCircle
    SYNTAX:
    dpc.[t/b/l/r] --or-- dpc.[top/bottom/left/right]
    DESCRIPTION:
    Illuminate half-circle (DPC) pattern
    -----------------------------------
    COMMAND:
    cdpc / colorDpc
    SYNTAX:
    cdpc.[rVal],[gVal].[bVal]) --or-- cdpc.[rgbVal]) --or-- cdpc
    DESCRIPTION:
    Illuminate color DPC (cDPC) pattern
    -----------------------------------
    COMMAND:
    an / annulus
    SYNTAX:
    an.[minNA*100].[maxNA*100]
    DESCRIPTION:
    Display annulus pattern set by min/max na
    -----------------------------------
    COMMAND:
    ha / halfAnnulus
    SYNTAX:
    ha.[type].[minNA*100].[maxNA*100]
    DESCRIPTION:
    Illuminate half annulus
    -----------------------------------
    COMMAND:
    dq / drawQuadrant
    SYNTAX:
    dq --or-- dq.[rVal].[gVal].[bVal]
    DESCRIPTION:
    Draws single quadrant
    -----------------------------------
    COMMAND:
    uv / lu
    SYNTAX:
    uv.0
    DESCRIPTION:
    Illuminate a uv LED
    -----------------------------------
    """

    def draw_hole(self, hole):
        """Illuminate LEDs around a single hole."""
        self.write('hole.' + str(hole))

    def _scan(self, command, delay):
        cmd = 'sc' + command

        if delay is None:
            return self.ask(cmd)
        else:
            return self.ask(cmd + ',' + f"{delay * 1000:.0f}")

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

        return self._scan('b', delay)

    def set_sequence_length(self, length):
        """Set sequence length in terms of independent patterns"""
        self.write('ssl,' + str(length))

    """
    COMMAND:
    ssv / setSeqValue
    SYNTAX:
    ssl.[1st LED #]. [1st rVal]. [1st gVal]. [1st bVal]. [2nd LED #]. [2nd rVal]. [2nd gVal]. [2nd bVal] ...
    DESCRIPTION:
    Set sequence value
    -----------------------------------
    COMMAND:
    rseq / runSequence
    SYNTAX:
    rseq,[Delay between each pattern in ms].[trigger mode for index 0].[trigger mode for index 1].[trigger mode for index 2]
    DESCRIPTION:
    Runs sequence with specified delay between each update.
    If update speed is too fast, a :( is shown on the LED array.
    """

    def run_sequence(self):
        pass

    """
    -----------------------------------
    COMMAND:
    rseqf / runSequenceFast
    SYNTAX:
    rseqf,[Delay between each pattern in ms].[trigger mode for index 0].[trigger mode for index 1].[trigger mode for index 2]
    DESCRIPTION:
    Runs sequence with specified delay between each update. Uses parallel digital IO to acheive very fast speeds. Only available on certain LED arrays.
    -----------------------------------
    """

    def print_sequence(self):
        """Prints sequence values to the terminal."""
        return self.ask('pseq')

    def print_sequence_length(self):
        """Prints sequence length to the terminal."""
        return self.ask('pseql')

    """
    COMMAND:
    sseq / stepSequence
    SYNTAX:
    sseq.[trigger output mode for index 0].[trigger output mode for index 1],
    DESCRIPTION:
    Runs sequence with specified delay between each update. If update speed is too fast, a: (is shown on the LED array.
    -----------------------------------
    """  # noqa

    def reset_sequence(self):
        """Resets sequence index to start."""
        self.write('reseq')

    def set_sequence_bit_depth(self, bitdepth):
        """Sets bit depth of sequence values(1, 8, or 16)"""
        self.write('ssbd.' + str(bitdepth))

    def trigger(self, index):
        """Output TTL trigger pulse to camera."""
        self.write('tr.' + str(index))

    def trigger_setup(self, index, pin_index, delay):
        """Set up hardware(TTL) triggering.

        SYNTAX:
        trs.[trigger index].[trigger pin index].['trigger delay between H and L pulses]
        """
        raise NotImplemented("I haven't implemented this yet")

    def trigger_print(self):
        """Prints information about the current i / o trigger setting"""
        return self.ask('ptr')

    def trigger_test(self, index):
        """Waits for trigger pulses on the defined channel."""
        self.write('trt.' + str(index))

    def draw_channel(self, led):
        """Draw LED by hardware channel(use for debugging)."""
        self.write('dc.' + str(led))

    def debug(self, value=None):
        """Set a debug flag. Toggles if value is None."""
        if value is None:
            self.write('dbg')
        elif value:
            self.write('dbg.1')
        else:
            self.write('dbg.0')

    def set_pin_order(self, red_pin, green_pin, blue_pin, led=None):
        """Sets pin order(R / G / B) for setup purposes."""

        # Big hack, the LED class basically does what we want,
        # Even though these are pins and not RGB values
        cmd = 'spo.' + str(LED(led=led, red=red_pin,
                               green=green_pin, blue=blue_pin))
        self.write(cmd)

    def delay(self, t):
        """Simply puts the device in a loop for the amount of time in seconds.
        """
        self.write('delay.' + f'{t*1000:.0f}')

    """
    COMMAND:
    pvals / printVals
    SYNTAX:
    pvals
    DESCRIPTION:
    Print led values for software interface
    - ----------------------------------
    COMMAND:
    pp / printParams
    SYNTAX:
    pp
    DESCRIPTION:
    Prints system parameters such as NA, LED Array z - distance, etc. in the format of a json file
    - ----------------------------------
    COMMAND:
    pledpos / printLedPositions
    SYNTAX:
    pledpos
    DESCRIPTION:
    Prints the positions of each LED in cartesian coordinates.
    -----------------------------------
    COMMAND:
    pledposna / printLedPositionsNa
    SYNTAX:
    pledposna
    DESCRIPTION:
    Prints the positions of each LED in NA coordinates(NA_x, NA_y, NA_distance
    """

    def discoparty(self, n_leds=1):
        """Runs a demo routine to show what the array can do."""
        self.write('disco,' + str(n_leds))

    def demo(self):
        """Runs a demo routine to show what the array can do."""
        self.write('demo')

    def water_drop_demo(self):
        """Water drop demo."""
        self.write('water')
