#!/usr/bin/env python3
"""
Created on Thu Mar 22 16:07:08 2018

@author: Mark
"""
from pyilluminate.illuminate import Illuminate
from pyilluminate.illuminate import LEDColor  # noqa analysis:ignore

i = Illuminate('COM4', timeout=.5)

# print(i.help())
print(i.about)
# i.scan_full()  # see https://github.com/zfphil/illuminate/issues/7
