# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 20:00:29 2021

@author: thijn
"""

import numpy as np
import time

from multiprocessing import Process, Queue #, get_logger, log_to_stderr

import matplotlib
matplotlib.use('tkagg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #NavigationToolbar2Tk
import matplotlib.pyplot as plt

import tkinter as tk
#from coremeasure import measurement # This imports the code that does the measurement

plt.close('all')
window = tk.Tk()

# The core loop of this function.
# A lot of what makes this code work is taken from thes following forum post:
# https://stackoverflow.com/questions/34764535/why-cant-matplotlib-plot-in-a-different-thread
# Particularly helpful was the example from the user "Noel Segura Meraz". When
# creating your own version based on that post, please note that some of this 
# user's code is somewhat outdated, e.g. the Matplotlib backend import.
def main():
    
    # Queue for communicating flag changes between processes.
    flag_running = Queue()
    
    # Create the bottons and add them to the UI. Notice that we need to 
    # anonymize the function we use as a command argument if we want to get
    # the behavior we want. 
    # https://stackoverflow.com/questions/6920302/how-to-pass-arguments-to-a-button-command-in-tkinter
    onbutton = tk.Button(window, text = "Start", command = lambda: switchon(flag_running,))      
    onbutton.pack()      
    offbutton =  tk.Button(window, text = "Halt", command = lambda: switchoff(flag_running,))      
    offbutton.pack()
    calibratebutton = tk.Button(window, text = "Calibrate", command = lambda: calibrate(flag_running,))      
    calibratebutton.pack()
    killbutton = tk.Button(window, text = "EXIT", command = lambda: kill(flag_running,))      
    killbutton.pack()  
    
    # Create a queue to share data between processes
    q = Queue()

    # Start the measurement
    measure=Process(None,measurement,args=(q, flag_running))
    measure.start()

    # Create the base plot
    plot()
         
    # Call a function to update the plot when there is new data
    updateplot(q)

    window.mainloop()
    print('Completed all code in main loop')
    
# This is where we define what signals we send to the flag queue when we
# press various buttons. We will use the following defintions:
# 1 = Measure and send to plotter
# 0 = Do not measure nor send to plotter
# 2 = Prepare for the thread to be closed   
def switchon(flag_running):  
    flag_running.put(1) 
    print('flag_running on:\t Measurement will start') 
          
def switchoff(flag_running): 
    flag_running.put(0)  
    print('flag_running off:\t Measurement has been halted')
    
def calibrate(flag_running): 
    flag_running.put(3)  
    print('flag_running off:\t Calibrating')
    
def kill(flag_running):  
    flag_running.put(2) 
    print('Terminating measurement')
    
    time.sleep(4)
    print('Shutting down Arduino')
    window.destroy()
    print('UI closed')

# This function initializes the plot. The lines, axes and canvas that it is
# built from are stored as global variables. This is so that they can be 
# updated later. We perform a similar routine for the data that drives
# the plot.
def plot():

    global line1X, line10X, line100X, ax1X, ax10X, ax100X, canvas
    global datastream, timestream, start_time

    fig = matplotlib.figure.Figure()
    ax1X = fig.add_subplot(1,3,1)
    ax10X = fig.add_subplot(1,3,2)
    ax100X = fig.add_subplot(1,3,3)
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    
    # These empty array will be filled with data as it comes in and will be
    # plotted.
    datastream = np.zeros((1,3))
    timestream = [0]
    start_time = time.time()
    
    line1X, = ax1X.plot([], []) 
    line10X, = ax10X.plot([], []) 
    line100X, = ax100X.plot([], []) 
    
    ax1X.set_xlabel('time (s)')
    ax1X.set_ylabel('voltage (V)')
    ax1X.set_title('1X')
    
    ax10X.set_xlabel('time (s)')
    ax10X.set_ylabel('voltage (V)')
    ax10X.set_title('10X')
    
    ax100X.set_xlabel('time (s)')
    ax100X.set_ylabel('voltage (V)')
    ax100X.set_title('100X')

    
    
def updateplot(q):
    
    global datastream
    # First, check if there is any data in the queue.
    try:
        result=q.get_nowait()
        
        if result !='Q': # Check if we are not at end of measurement
             print(f'Fetched the following data: {result}')
             
             # This code determines what to plot. Specifically, it 
             # concatenates the old data ith the new data from the queue
             datastream = np.append(datastream, [result[1:]], axis = 0)
             timestream.append(result[0])
             now = timestream[-1]
             
             # Calculate the new axes
             ax1X.set_xlim([0 ,now + .1]) # 0.1 to add border
             ax1X.set_ylim([0, np.max(datastream[:,0]) + .1])
             
             ax10X.set_xlim([0 ,now + .1]) # 0.1 to add border
             ax10X.set_ylim([0, np.max(datastream[:,1]) + .1])
             
             ax100X.set_xlim([0 ,now + .1]) # 0.1 to add border
             ax100X.set_ylim([0, np.max(datastream[:,2]) + .1])
             
             # This does the plotting
             line1X.set_data(timestream, datastream[:,0])
             line10X.set_data(timestream, datastream[:,1])
             line100X.set_data(timestream, datastream[:,2])
             
             ax1X.draw_artist(line1X)
             ax10X.draw_artist(line10X)
             ax100X.draw_artist(line100X)
             
             canvas.draw()
             window.after(500,updateplot,q)
        
        else: # Has reached end of data stream from measuremetn
             print('End of queue')
    except: 
        #print("empty")
        window.after(500,updateplot,q)
        
def measurement(q, flag_running):
    # Set plotting interval. By this we mean the number of measurements we do
    # per plot update, i.e. if this is set to 10 the plot will only update 
    # every 10 measurements.
    INTERVAL = 3
    
    # Set a forced delay between measurements
    DELAY = 1
    
    import pyfirmata
    import tables 
    
    filename='measurement.h5'

    # https://stackoverflow.com/questions/30376581/save-numpy-array-in-append-mode
    COLUMNS = 4
    
    f = tables.open_file(filename, mode='w')
    atom = tables.Float64Atom()
    
    array_c = f.create_earray(f.root, 'data', atom, (0, COLUMNS))
    
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
    
    def DACwrite(voltage, DAC='A', freq=18): 
        # Overkill frequency to make sure this runs as fast as possible
        # Defaults to DAC A, Clock frequency in Hz
        assert voltage <= 4.096, 'The requested voltage out is too high'
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
        time.sleep(.1)    
        
        # Send
        start = time.time()
        
        for ii in range(16):
            mosi.write(int(data[ii]))   # Send single bit
            time.sleep(1/freq*.5)
            sck.write(1)                # Clock HIGH
            time.sleep(1/freq*.5)
            sck.write(0)                # Clock LOW
        
        # Deselect DAC Chip
        time.sleep(.1)  
        cs.write(1)
        
        final_freq = int(1/(time.time()-start/16))
        
        return final_freq

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
        if (power < 10): power = 10
            
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
            
        DACwrite(0)
        time.sleep(0.5)
        DACshutdown()
    
    # ------------------------------------------------------------------------
    # MEASUREMENT CODE
    # This is will perform the measurements over time
    # ------------------------------------------------------------------------
    
    arduino = pyfirmata.ArduinoNano('COM5')
    time.sleep(0.5)
    it = pyfirmata.util.Iterator(arduino)
    it.start()
    time.sleep(0.5)
    a0 = arduino.get_pin('a:0:i') #1X
    a1 = arduino.get_pin('a:1:i') #10X
    a2 = arduino.get_pin('a:2:i') #100X
    time.sleep(0.5)
    
    setupRGB(arduino)
    
    time.sleep(0.5)
    RGBon('R',power=90)
    start = time.time()
    
    time.sleep(1)
    
    # Check whether the current value of the flag that determines whether or 
    # not we should be measuring and passing those measurements on to the plot
    flag = 0
    i = 0
    while True:
        time.sleep(DELAY)
        try:
            flag = flag_running.get_nowait()
        except:
            ""
            #print("No flag") # Dummy code
        
        # If the flag setting is 1 measure and send one in three measurements
        # to the plotter.
        if flag == 1:
            data1X = a2.read() * 5
            data10X = a0.read() * 5/10
            data100X = a1.read() * 5/100
            timepoint = time.time()-start
        
            # Send to plotter over a certain interval
            if (not i % INTERVAL):
                q.put([timepoint, data1X, data10X, data100X])
                
            # Store to file
            x = [[timepoint, data1X, data10X, data100X]]
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
            
        i += 1
    q.put('Q') # Signifies end of measurement.
   

   
if __name__ == '__main__':
    main()
 
    
