"""Control the SciMicroscopy Illuminate with ease.

This module defines functions to control the SciMicroscopy module in a modern
(Python 3) fashinon.

Raise exceptions on failure, don't worry about "set" and "get" methods.

Copyright (C) 2018, Ramona Optics, Inc.
"""

from .illuminate import Illuminate

from ._version import __version__  # noqa

__all__ = [
    'Illuminate',
]
