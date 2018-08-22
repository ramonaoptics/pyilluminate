"""Control the SciMicroscopy Illuminate with ease.

This module defines functions to control the SciMicroscopy module in a modern
(Python 3) fashinon.

Raise exceptions on failure, don't worry about "set" and "get" methods.

Copyright (C) 2018, Ramona Optics, Inc.
"""

from .illuminate import Illuminate  # noqa
from .illuminate import LEDColor  # noqa

from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
