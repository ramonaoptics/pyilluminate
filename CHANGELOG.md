## 0.3.0.dev

 * Illuminate.led_positions is now an xarray instead of a numpy struct array.
 * ``owl.instruments.Illuminate.positions_as_xarray()`` is deprecated in favour of ``owl.instruments.Illuminate.led_positions``.

## release-0.2.9

 * Better access to the color/bightness property
 * The array will turn itself off once you close python
 * Clears LEDs when setting individual LEDs too.
