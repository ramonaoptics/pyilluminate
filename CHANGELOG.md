## 0.3.2 (2019/08/19)

 * Fixed up a typo that would cause an error to occur in `positions_as_xarray`.

## 0.3.1 (2019/05/22)

 * Improved the error message when trying to open an Serial connection that is already in use.

## 0.3.0

 * Illuminate.led_positions is now an xarray instead of a numpy struct array.
 * ``Illuminate.positions_as_xarray()`` is deprecated in favour of ``Illuminate.led_positions``.
 * The attribute ``Illuminate.color`` can now be set with either a tuple or a simple scalar.

## release-0.2.9

 * Better access to the color/bightness property
 * The array will turn itself off once you close python
 * Clears LEDs when setting individual LEDs too.
