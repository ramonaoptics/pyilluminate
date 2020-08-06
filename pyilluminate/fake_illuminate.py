from .illuminate import Illuminate
import numpy as np
import xarray as xr


class FakeIlluminate(Illuminate):
    def __init__(self, *args, N_leds=377, **kwargs):
        """Basic fake illuminate device.

        Use only for testing the callback and metadata.
        """
        kwargs.setdefault('precision', 8)
        self.N_leds = N_leds
        self.brightness = 1
        self.autoclear = True
        self._precision = kwargs['precision']
        if self._precision != 8:
            raise ValueError(
                "FakeIlluminate not implemented for precisions other than 8.")

        self._led_positions = xr.DataArray(
            # TODO: set this as np.empty when below is doen
            np.zeros((self.N_leds, 3)),
            dims=['led_number', 'zyx'],
            coords={'led_number': np.arange(self.N_leds),
                    'zyx': ['z', 'y', 'x']})

        self._led_positions[:, 1] = np.arange(self.N_leds) * 1E-3
        self._led_positions[:, 2] = np.arange(self.N_leds) * 1E-3

        uv_leds = self.uv_leds

        chroma = xr.DataArray(
            np.full(self.N_leds, fill_value='rgb', dtype='<U3'),
            dims=['led_number'])
        chroma[uv_leds] = 'uv'
        self._led_positions = self._led_positions.assign_coords(
            chroma=chroma)

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

        # Clear the LEDs
        self.led = None

    @property
    def autoclear(self):
        return self._autoclear

    @autoclear.setter
    def autoclear(self, value):
        self._autoclear = bool(value)

    def open(self):
        pass

    @property
    def version(self):
        return '1.20.2'

    @property
    def device_name(self):
        return 'fake-illuminate'

    def close(self):
        pass

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    @property
    def led(self):
        return self._led

    @led.setter
    def led(self, leds):
        if leds is None:
            clear_result = self.clear()
            return clear_result

        if isinstance(leds, np.ndarray):
            # As 1D
            leds = leds.reshape(-1).tolist()

        try:
            self._led = list(leds)
        except TypeError:
            # Make it a tuple
            self._led = (leds, )

    @property
    def brightness(self):
        if (self._color[0] == self._color[2] and
                self._color[1] == self._color[1]):
            return self._color[0]
        else:
            raise ValueError('The RGB values are not equal. To access their '
                             'value, use the `color` property instead.')

    @brightness.setter
    def brightness(self, b):
        self.color = (b, b, b)

    @property
    def color(self):
        """LED array color."""
        return self._color

    @color.setter
    def color(self, c):
        self._color = c

    def clear(self):
        self._update_led_state([], force_clear=True)

    def fill_array(self, led_type='rgb'):
        # Ignore led_type for the fake illuminate device
        self._led = list(range(self.N_leds))

    @property
    def led_positions(self):
        return self._led_positions

    @property
    def uv_leds(self):
        return [self.N_leds - 1]

    @property
    def rgb_leds(self):
        return list(range(self.N_leds - 1))

    @property
    def all_leds(self):
        return list(range(self.N_leds))

    @property
    def serial_number(self):
        return '123456'
