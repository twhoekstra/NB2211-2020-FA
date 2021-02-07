# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 23:38:11 2021

@author: thijn
"""

# Final code
import tables 
import numpy as np
import time
import matplotlib.pyplot as plt

filename='measurement.h5'

# Opening data from file
# https://stackoverflow.com/questions/30376581/save-numpy-array-in-append-mode
f = tables.open_file(filename, mode='r')
print('opened')
data = f.root.data[:,:]

time.sleep(1)
f.close()
print('closed')

# Plot Data
fig = plt.figure(figsize=(8,6))

ax = np.empty((3,1), dtype=object)
#line = np.empty((3,3), dtype=object)

for ii in range(3):
    ax[ii] = fig.add_subplot(1,3,ii+1)
    ax[ii][0].set_xlabel('time (s)') # [0] needed to "unpack" object from array
    ax[ii][0].set_ylabel('Intensity (%)')
    ax[ii][0].set_title(['1X','10X','100X'][ii])
  

for ii in range(3):
    jj = 0
    for color in ['r','g','b']:
        ax[ii][0].plot(data[:,0], data[:,1+ii+4*jj]*100, color)
        jj += 1


fig.tight_layout() # Prevents axis labels from overlaping with the adjacent plot

print('done')