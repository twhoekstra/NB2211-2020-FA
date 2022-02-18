# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 20:00:29 2021

@author: thijn
"""

import numpy as np
import time

from multiprocessing import Process, Queue

import matplotlib
matplotlib.use('tkagg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg 
import matplotlib.pyplot as plt
import tkinter as tk


plt.close('all')
window = tk.Tk()

# The core loop of this function.
# A lot of what makes this code work is taken from the following forum post:
# https://stackoverflow.com/questions/34764535
# Particularly helpful was the example from the user "Noel Segura Meraz". When
# creating your own version based on that post, PLEASE NOTE that some of this 
# user's code is somewhat outdated, e.g. the Matplotlib backend import. 
def main():
    
    # Queue for communicating flag changes between processes.
    flag_running = Queue()
    
    # Create a queue to share data between processes
    q = Queue()

    # BUTTON AREA
    # ------------------------------------------------------------------------
    # Create the bottons and add them to the UI. Notice that we need to 
    # anonymize the function we use as a command argument if we want to get
    # the behavior we want. 
    # https://stackoverflow.com/questions/6920302/
    onbutton    = tk.Button(window, 
                            text = "Start", 
                            command = lambda: switchon(flag_running,))      
    offbutton   = tk.Button(window, 
                            text = "Halt", 
                            command = lambda: switchoff(flag_running,))      
    calibutton  = tk.Button(window, 
                            text = "Calibrate", 
                            command = lambda: calibrate(flag_running,))      
    onplotbutton    = tk.Button(window, 
                                text = "Plot On", 
                                command = lambda: ploton(flag_running,))      
    offplotbutton   = tk.Button(window, 
                                text = "Plot Off", 
                                command = lambda: plotoff(flag_running,))      
    killbutton  = tk.Button(window, 
                            text = "EXIT", 
                            command = lambda: kill(flag_running,))      
    onbutton.pack()
    offbutton.pack()
    calibutton.pack()
    onplotbutton.pack()
    offplotbutton.pack()
    killbutton.pack()
    # ------------------------------------------------------------------------
    
    # Start the measurement
    measure=Process(None,measurement,args=(q, flag_running))
    measure.start()

    plot() # Create plot
         
    updateplot(q) # Update the plot whenever there is new data

    window.mainloop()
    print('Completed all code in main loop')
    
measure_text = 'OFF' # Global variable to keep track of whether measuring is on
# or off so we can print more informative information when changing plotting 
# settings
    
# This is where we define what signals we send to the flag queue when we
# press various buttons. We will use the following defintions:
# 1 = Measure and send to plotter
# 0 = Do not measure nor send to plotter
# 2 = Prepare for the thread to be closed   
# 3 = Go through the calibration steps
# 4 = Turn plotting off
# 5 = Turn plotting on 
def switchon(flag_running):  
    global measure_text
    flag_running.put(1) 
    print('Measuring ON:\t Measurement will start') 
    measure_text = 'ON'
          
def switchoff(flag_running): 
    global measure_text
    flag_running.put(0)  
    print('Measuring OFF:\t Measurement has been halted')
    measure_text = 'OFF'
    
def plotoff(flag_running): 
    flag_running.put(4)  
    print(f'Measuring {measure_text}:\t Live plotting OFF')
    
def ploton(flag_running): 
    flag_running.put(5)  
    print(f'Measuring {measure_text}:\t Live plotting ON')
    
def calibrate(flag_running): 
    flag_running.put(3)  
    print('Measuring OFF:\t Calibrating')
    
def kill(flag_running):  
    flag_running.put(2) 
    print('Terminating measurement')
    
    # Give the Arduino time to wrap up its work. It might be in the middle of
    # a measurement or be writing to the DAC, etc.
    time.sleep(4)
    
    print('Shutting down Arduino')
    window.destroy()
    print('UI closed')

# This function initializes the plot. The lines, axes and canvas that it is
# built from are stored as global variables. This is so that they can be 
# updated later. We perform a similar routine for the data that drives
# the plot.
def plot():

    global line, ax, canvas
    global datastream, timestream

    fig = matplotlib.figure.Figure()
    
    # We are going to store the matplotlib objects in a numpy matrix. This is
    # so we don't have do make a global variable for each line and axis, etc.
    # That would look ugly.
    ax = np.empty((3,1), dtype=object)
    line = np.empty((3,3), dtype=object)
    
    for ii in range(3):
        ax[ii] = fig.add_subplot(1,3,ii+1)
        # [0] needed to "unpack" object from array so we can run a method 
        ax[ii][0].set_xlabel('time (s)') 
        ax[ii][0].set_ylabel('Intensity (%)')
        ax[ii][0].set_title(['1X','10X','100X'][ii])
  
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    
    # These empty array will be filled with data as it comes in and will be
    # plotted.
    # 'timestream' needs to empty if the first dimension of the 'datastream'
    # array is of length 0
    datastream = np.zeros((0,3,3))
    timestream = [] 
    
    # Initialize the lines and the colors!
    for ii in range(3):
        jj = 0
        for color in ['r','g','b']:
            line[ii,jj], = ax[ii][0].plot([], [], color)
            jj += 1
            
    fig.tight_layout() # So the axis labels dont overlap with the adjacent plot

def updateplot(q):
    
    global datastream
    # First, check if there is any data in the queue.
    try:
        result=q.get_nowait()
        
        if type(result) is np.ndarray: # Check if not at end of measurement
            
            # Uncomment for debugging 
            # print(f'Fetched the following data: {result}')
             
            # This code determines what to plot. Specifically, it 
            # concatenates the old data ith the new data from the queue
            # We multiply by 100 to get percentage value
            datastream = np.append(datastream, [result[:,1:]*100], axis = 0)
            timestream.append(result[0,0])
            now = timestream[-1]
             
            # Calculate the new axes
            for ii in range(3): # Iterate over 1X, 10X, and 100X plots
                ax[ii][0].set_xlim([0 ,now + .1]) # 0.1 to add border
                ax[ii][0].set_ylim([0, np.max(datastream[:,:,ii]) + .1])
            
            # Draw
            for ii in range(3): # Iterate over 1X, 10X, and 100X plots
                for jj in range(3): # Iterate over colors
                    line[ii,jj].set_data(timestream, datastream[:,jj,ii])
              
            for ii in range(3): # Iterate over 1X, 10X, and 100X plots
                for jj in range(3): # Iterate over colors
                    ax[ii][0].draw_artist(line[jj,ii])
                 
            canvas.draw()
            window.after(500,updateplot,q)
        
        else: # Reached end of measurement
            #result !='Q'
             print('End of queue')
    except: 
        # Runs when there is no data in the queue. Check again if there is 
        # anything to plot some specified time in the future.
        # print("empty")
        window.after(1000,updateplot,q) 
        
# The actual measurement code        
def measurement(q, flag_running):
    # Set plotting interval. By this we mean the number of measurements we do
    # per plot update, i.e. if this is set to 10 the plot will only update 
    # every 10 measurements.
    INTERVAL = 1
    
    # Set the maximum amount of points plotted at the start of the measurement.
    # This can be overridden via the buttons. Implemented to prevent issues 
    # caused when a user starts a long measurement without turning off the 
    # plotting: this will cause the program to crash.
    MAX_POINTS = 25
    
    # Power of LED in percent
    POWER = 25
    
    # Set a forced delay between measurements
    DELAY = .6
    LONG_DELAY = 1
    RGB_DELAY = 2.5 # Delay between switching color and measuring
    
    # File name to store data as HDF5 file.
    filename='measurement.h5'
    
    import pyfirmata
    import tables 
    
    # Set up the file on disk to store data to.
    # https://stackoverflow.com/questions/30376581
    COLUMNS = 12 # = (No. Colors)*(No. Channels +1)
    f = tables.open_file(filename, mode='w')
    atom = tables.Float64Atom()
    array_c = f.create_earray(f.root, 'data', atom, (0, COLUMNS))
    
    
    # FUNCTION DEFINITION AREA
    # Note: it seems to be hard to get import functions from an external file
    # into the 'measurement' function when it is run using 'multiprocessing'.
    # This is an ugly workaround.
    
    # ------------------------------------------------------------------------
    # DAC CODE
    # Set up arduino.
    # Space for functions that allow us to control the Digital to Analog
    # Converter (DAC) on the Alpaca board
    # ------------------------------------------------------------------------
    def DACsetup(arduino):
        # Sets up DAC for Arduino NANO
        #SPI: 10 (SS), 11 (MOSI), 12 (MISO), 13 (SCK).
        
        # Setup pins    
        global cs
        global mosi
        global sck
        
        cs = 1
        time.sleep(1)
        
        cs = arduino.get_pin('d:10:o') #SS
        mosi = arduino.get_pin('d:11:o') #MOSI
        sck = arduino.get_pin('d:13:o') #SCLK
            
        # Deselect DAC
        cs.write(1)
        sck.write(0) # Ensure clock output at low
            
        # Confirm setup
        global DACisSetUp
        DACisSetUp = True
        
    def DACfastWrite(voltage, DAC='A'): 
        # Ulgy code that should run faster
        # Defaults to DAC A, Clock frequency in Hz
        assert voltage <= 4.096 , 'The requested voltage out is too high'
        assert DAC == 'A' or DAC == 'B', 'Please input as string either A or B'
        assert DACisSetUp , 'Please set up the DAC first'
    
        # **DETERMINE CORRECT DAC SETTINGS**
        # Set to 0 for DAC A. Set to 1 for DAC B
        gain_select = 1
        if voltage > 2.04975: gain_select = 0
        
        # Set to 1 for unity gain. Set to 0 for gain = 2.
        dac_select = 0
        if DAC == 'B': dac_select = 1
        
        # **CALCULATE OUTPUT SIGNAL**
        # Max 4095 --> 2.04975V
        signal = int(voltage*4095/(2.04975*(2-gain_select)) )
        
        # Generate config bits and write full datastream
        config = str(dac_select)+'0'+str(gain_select)+'1'
        data = format(signal, '012b')
        data = config + data
        
        # Select DAC Chip
        cs.write(0)
        #time.sleep(.1)    
        
        # Send
        for ii in range(16):
            mosi.write(int(data[ii]))   # Send single bit
            #time.sleep(1/freq*.5)
            sck.write(1)                # Clock HIGH
            #time.sleep(1/freq*.5)
            sck.write(0)                # Clock LOW
        
        # Deselect DAC Chip
        #time.sleep(.1)  
        cs.write(1)
        return
    
    def DACshutdown(DAC='A', freq=10):
        # Defaults to DAC A, Clock frequency in Hz
        assert DAC == 'A' or DAC == 'B', 'Please input as string either A or B'
        assert DACisSetUp , 'Please set up the DAC first'
    
        global cs
        global mosi
        global sck
        global arduino
    
        # **DETERMINE CORRECT DAC SETTINGS**
        # Set to 0 for DAC A. Set to 1 for DAC B
        dac_select = 0
        if DAC == 'B': dac_select = 1
        
        # **CALCULATE OUTPUT SIGNAL**
        # Generate config bits and write full datastream
        data = str(dac_select)+'010000000000000'
        
        # Select DAC Chip
        cs.write(0)
        time.sleep(.1)    
        
        # Send
        for ii in range(16):
            mosi.write(int(data[ii]))   # Send single bit
            time.sleep(1/freq*.5)
            sck.write(1)                # Clock HIGH
            time.sleep(1/freq*.5)
            sck.write(0)                # Clock LOW
        
        # Deselect DAC Chip
        time.sleep(.1)  
        cs.write(1)
    
    # ------------------------------------------------------------------------
    # LED CODE    
    # This is where the code that controls the RGB LED lives. It simplifies   
    # the process of switching the colors of the LED
    # ------------------------------------------------------------------------
    def setupRGB(arduino, pinR = 5, pinG = 3, pinB = 4):
        global LEG_G, LEG_B, LEG_R
        global isOn
        
        LEG_G = arduino.get_pin(f'd:{pinG}:o')
        LEG_B = arduino.get_pin(f'd:{pinB}:o')
        LEG_R = arduino.get_pin(f'd:{pinR}:o')
        LEG_G.write(0)
        LEG_B.write(0)
        LEG_R.write(0)
        
        DACsetup(arduino)
        
        isOn = False

    # Power in %
    def RGBon(color, power=50):
        # Built-in safety threshold that can be set. The DAC will not output
        # a voltage larger than this
        SAFETY = 4.096 
        
        global isOn
        global previous_LED
        global previous_voltage
        
        assert color in ['R','G','B'], 'The color input should be either R, G or B'
        
        if (power > 100): power = 100
        if (power < 1): power = 1
            
        # Max voltage at LED driver input is 0.78V. Az voltage divider will 
        # ensure that the output is stepped down appropriately
        voltage = 4.096 * (power/100)
            
        # SAFETY CODE. DO NOT REMOVE
        if (voltage > SAFETY):
            print('LED overload safety triggered')
            return
        
        if      color == 'R': current_LED = LEG_R
        elif    color == 'G': current_LED = LEG_G
        elif    color == 'B': current_LED = LEG_B
        
        if not isOn:
            current_LED.write(1)
            DACfastWrite(voltage)
            
            isOn = True
            
        
        else: # An LED is already turned on
            if (voltage == previous_voltage):
                previous_LED.write(0)
                time.sleep(0.1)
                current_LED.write(1)
                
            else:
                previous_LED.write(0)
                time.sleep(0.1)
                current_LED.write(1)
                DACfastWrite(voltage)
                
        previous_LED = current_LED
        previous_voltage = voltage

    def RGBshutdown():
    
        LEG_G.write(0)
        LEG_B.write(0)
        LEG_R.write(0)
            
        DACfastWrite(0)
        time.sleep(0.5)
        DACshutdown()
    
    # ------------------------------------------------------------------------
    # MEASUREMENT CODE
    # This is will perform the actual measurements
    # ------------------------------------------------------------------------
    
    arduino = pyfirmata.ArduinoNano('COM5')
    time.sleep(DELAY)
    it = pyfirmata.util.Iterator(arduino)
    it.start()
    time.sleep(DELAY)
    a0 = arduino.get_pin('a:0:i') #10X
    a1 = arduino.get_pin('a:1:i') #100X
    a2 = arduino.get_pin('a:2:i') #1X
    
    buzzer = arduino.get_pin('d:2:o')
    time.sleep(DELAY)
    setupRGB(arduino)
    
    # Initial Calibration. The flag is set to zero so the measurement does not
    # start immediately after the calibration
    flag = 0 
    while True:
        time.sleep(LONG_DELAY)
        try:
            # Wait for calibration button to be pressed
            flag = flag_running.get_nowait()  
        except:
            ""
        
        if flag == 3: # Calibrating mode. This means the button was pressed
            reading = np.zeros(3)
            bases = np.zeros((3,3))
            ii = 0
            for color in ['R', 'G', 'B']: # Iterate over colors
                RGBon(color,power=POWER)
                time.sleep(RGB_DELAY)
                
                reading[0] = a2.read() #1X
                time.sleep(DELAY)
                reading[1] = a0.read() #10X
                time.sleep(DELAY)
                reading[2] = a1.read() #10X
                time.sleep(DELAY + LONG_DELAY)
            
                # Store the calibration levels row by row
                bases[ii,:] = reading #1X , then 10X, then 100X
                ii += 1 
            
            # End of calibration. Notify user by sounding buzzer
            time.sleep(LONG_DELAY)
            buzzer.write(1)
            time.sleep(DELAY)
            buzzer.write(0)
            break
    
    # Start of measurement loop
    start = time.time()
    time.sleep(DELAY)
    ii = 0
    reading = np.zeros(3)
    intensities = np.zeros((3,4)) # Four columns to accomodate time
    
    # Local variables to keep track whether or not we are actively plotting and
    # measuring. During the loop: look for flag changes due to the buttons and 
    # update these values accordingly
    isMeasuring = False
    isPlotting = True
    
    # Check the current value of the flag. This determines whether or 
    # not we should be measuring and passing those measurements on to the plot
    while True:
        time.sleep(DELAY)
        try:
            flag = flag_running.get_nowait()
        except:
            ""
            #print("No flag") # Dummy code
        
        # Update local variables based on the external input.
        if flag == 1: isMeasuring = True
        if flag == 0: isMeasuring = False
        if flag == 4: isPlotting = False
        if flag == 5: isPlotting = True
        
        # Use these values to take appropriate action
        if isMeasuring:
            timepoint = time.time()-start
            
            jj = 0
            for color in ['R', 'G', 'B']:
            
                RGBon(color,power=POWER)
                time.sleep(RGB_DELAY)
                reading[0] = a2.read()
                time.sleep(DELAY)
                reading[1] = a0.read()
                time.sleep(DELAY)
                reading[2] = a1.read()
                time.sleep(DELAY*2)
                
                #1X , then 10X, then 100X
                intensities[jj,1:] = np.divide(reading, bases[jj,:]) 
                jj += 1 
            
            intensities[0,0] = timepoint
        
            # Send to plotter over a certain interval
            if (not ii % INTERVAL) & isPlotting:
                q.put(intensities)
                
                if (ii/INTERVAL)>MAX_POINTS:
                    isPlotting = False # Auto-shutdown of plotting
                
            # Store to file
            x = [intensities.flatten()]
            array_c.append(x)
                
        # If the flag is set to 2 then the thread will be shutting down
        # shortly. To prepare for this, close the serial connection with the 
        # Arduino. If we do not do this, we cannot open the port next time we
        # run the code. 
        if flag == 2:
            f.close() # Close the file
            RGBshutdown()
            time.sleep(0.5)
            arduino.sp.close()
            
            return
            
        ii += 1
    q.put('Q') # Signifies end of measurement.
   
if __name__ == '__main__':
    main()
 
    
