# -*- coding: utf-8 -*-
"""
Created on Thu Mar 22 16:07:08 2018

@author: Mark
"""
from pyilluminate.illuminate import Illuminate

i = Illuminate('COM4', timeout=.1)

print(i.help())
# i.scan_full()  # see https://github.com/zfphil/illuminate/issues/7
