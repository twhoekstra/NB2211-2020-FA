# -*- coding: utf-8 -*-
"""
Created on Thu Feb  4 23:38:11 2021

@author: thijn
"""

# PLOT SETTINGS
filename = 'measurement.h5'
START = 25      # Use to set what the first data point to plot should be
WINDOW = 100    # The size of the window used for the rolling average

# tkagg backend is used for live plotting in main program.
# so we need to switch back to the standard backend
import matplotlib
matplotlib.use('Agg') 

import tables 
import numpy as np
import time
import matplotlib.pyplot as plt
plt.close('all')

# Rolling average function, made using help from:
# https://stackoverflow.com/questions/14313510/
def moving_average(x, w):
    return np.convolve(x, np.ones(w), 'valid') / w

# Opening data from HDF5 file. Thanks to:
# https://stackoverflow.com/questions/30376581/save-numpy-array-in-append-mode
f = tables.open_file(filename, mode='r')
print('opened')
data = f.root.data[:,:]

time.sleep(1)
f.close()
print('closed')

# Plotting 
fig = plt.figure(figsize=(10,6))

ax = np.empty((3,1), dtype=object)

# Set the labels and titles for the plots
for ii in range(3):
    ax[ii] = fig.add_subplot(1,3,ii+1)
    # [0] needed to "unpack" object from array so we can run a method 
    ax[ii][0].set_xlabel('time (s)') 
    ax[ii][0].set_ylabel('Intensity (%)')
    ax[ii][0].set_title(['1X','10X','100X'][ii])
  
# Plot the raw data as it is stored in the HDF5 file. Use pastel colors to 
# differentiate from the average
for ii in range(3): # Iterate over gains
    jj = 0
    for color in ['lightcoral','lightgreen','cornflowerblue']:
        ax[ii][0].plot(data[START:,0], 
                       data[START:,1+ii+4*jj]*100, 
                       color = color, 
                       marker = 'd', 
                       label = "Data" if ii == 0 else "")
        jj += 1

# Plot a rolling average of the data for clarity. We will plot these using the
# 'default' colors for red, green, and blue.
for ii in range(3): # Iterate over gains
    jj = 0
    for color in ['r','g','b']:
        ax[ii][0].plot(data[START+WINDOW-1:,0], 
                       moving_average(data[START:,1+ii+4*jj]*100, WINDOW), 
                       color = color, 
                       linestyle = '-', 
                       label = "Average" if ii == 0 else "")
        jj += 1

fig.legend()
fig.tight_layout() # Prevent axis labels from overlaping with the adjacent plot

print('done')