## 0.6.5 (2021/04/13)

 * Avoid bogus errors on the system trying to recover from a serial error
   caused by undefined `_led_state`.

## 0.6.4 (2021/03/20)

 * Fixed typo in docs of ``Illuminate.find_max_brightness`` causing a section
   header to be mis-identified.

## 0.6.3 (2021/03/08)

 * Fixed a bug where estimating the maximum brigthness can return values that
   are too large for small numbers of LEDs.

## 0.6.2 (2021/03/04)

 * Docstring formatting fixes.

## 0.6.1 (2021/03/01)

 * Add a property for getting and setting the maximum allowed current on the board.
 * Add a property for getting the maximum current per LED channel.
 * Add a function for calculating the maximum allowed brightness values.

## 0.6.0 (2020/12/29)

 * Remove ``LEDColor``.

## 0.5.19 (2020/09/05)

 * Fix a bug where the previous pattern would continue to appear when sending
   long lists of LEDs.

## 0.5.18 (2020/08/23)

 * The ``led`` attribute is not available to read before ever setting it.
## 0.5.17 (2020/08/16)

 * Avoid buffer overflow errors by ensuring that strings are cut in 64 bytes.
   This may make custom LED commands slower.

## 0.5.16 (2020/08/06)

 * FakeIlluminate device now has an ignored `led_type` parameter for fill_array.

## 0.5.15 (2020/08/05)

 * LED state now correctly initialized to avoid spurious errors.

## 0.5.14 (2020/08/05)

 * LED boards can now report the value of the color for all LEDs in the
   `led_colors` property.

## 0.5.13 (2020/08/04)

 * Better detection of autoUpdate feature without loading the full Help file.

## 0.5.12 (2020/08/04)

 * Enable downstream to override how led_positions are obtained.

## 0.5.11 (2020/07/27)

 * Better recovery from serial exceptions during boot up procedure.

## 0.5.10 (2020/07/22)

 * Ignore serial communication errors upon closing are ignored.

## 0.5.9 (2020/07/19)

 * Fix openning device by serial number.

## 0.5.8 (2020/07/19)

 * Better handler for lock timeout for downstream developers.

## 0.5.7 (2020/07/19)

 * Multiple users can attempt to use the pyilluminate boards at the same time.

## 0.5.6 (2020/07/19)

 * Bugfix: LED boards can be open by specifying ``port`` parameter again.
 * Private functions for lock and unlock for downstream developers.

## 0.5.5 (2020/07/06)

 * Better support for very long lists of LEDs (best with firmware update).
 * System now raises an error upon using the common typo `Illuminate.leds = ...`
 * Locks are used to avoid multiple applications from attempting to control the
   Illuminate board at the same time.

## 0.5.4 (2020/06/30)

 * Distribution name changed from pyIlluminate to pyilluminate.

## 0.5.3 (2020/06/29)

 * Initial support for 16 bit precision drivers.

## 0.5.2 (2020/06/28)

 * First release on GitHub.

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
