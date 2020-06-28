## 0.5.1 (2020/06/27)

 * Initialize all LED arrays with max brightness.

## 0.5.0 (2020/06/27)

 * Autoclear enable/disable functionality can be used to draw LEDs with
   different colors.
 * Deprecate the use of the `LEDColor` class.

## 0.4.7 (2019/12/12)

 * Better error messages when a device isn't found.

## 0.4.6 (2019/11/18)

 * list_serial_numbers returns serial numbers again

## 0.4.5 (2019/11/14)

 * Not finding any devices raises a better error message.

## 0.4.4 (2019/09/20)

 * Package no longer vendors dataclasses

## 0.4.3 (2019/09/20)

 * Package is no a noarch package.

## 0.4.2 (2019/09/19)

 * JSONDecodeError are alleviated in Windows making opening the LED board more
   consistent.

## 0.4.1 (2019/09/01)

 * BUGFIX: Setting the buffer size now only occurs on platforms that support
   it. This bug was introduced in 0.4.0 and manifested itself as the inability
   to open the device on linux

## 0.4.0 (2019/08/26)

 * Refactored how devices are identified. They are not identified by their
   serial numbers instead of their MAC Address. This avoids port knocking and
   ensures that openning devices is now faster especially when trying to
   connect to multiple Illuminate devices connected to a single computer.

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
