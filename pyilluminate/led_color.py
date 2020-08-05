from dataclasses import dataclass
from typing import Optional
from warnings import warn


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
             "Please use a standard tuple of 3 or List of 3 elements.",
             stacklevel=2)
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
