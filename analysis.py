# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 23:38:11 2021

@author: thijn
"""

# Final code
import tables 
import time
time.sleep(.5)

filename='measurement.h5'

# https://stackoverflow.com/questions/30376581/save-numpy-array-in-append-mode
COLUMNS = 3

f = tables.open_file(filename, mode='r')
print('opened')
print(f.root.data[-4:,:]) # e.g. read from disk only this part of the dataset

time.sleep(1)
f.close()

print('closed')