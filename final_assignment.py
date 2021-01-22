# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 20:00:29 2021

@author: thijn
"""

from random import random
import numpy as np
import time
from multiprocessing import Process, Lock, Value, Queue, get_logger, log_to_stderr
import matplotlib
matplotlib.use('tkagg')
from matplotlib.backends.backend_tkagg import ( FigureCanvasTkAgg, NavigationToolbar2Tk)
import matplotlib.pyplot as plt
import tkinter as tk

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
    
def kill(flag_running):  
    flag_running.put(2) 
    print('Terminating measurement')
    
    time.sleep(3)
    print('Shutting down Arduino')
    window.destroy()
    print('UI closed')

# This function initializes the plot. The lines, axes and canvas that it is
# built from are stored as global variables. This is so that they can be 
# updated later. We perform a similar routine for the data that drives
# the plot.
def plot():

    global line, ax, canvas
    global datastream, timestream, start_time

    fig = matplotlib.figure.Figure()
    ax = fig.add_subplot(1,1,1)
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    
    # These empty array will be filled with data as it comes in and will be
    # plotted.
    datastream = []
    timestream = []
    start_time = time.time()
    
    line, = ax.plot([], []) 
    
    
def updateplot(q):
    # First, check if there is any data in the queue.
    try:
        result=q.get_nowait()
        
        if result !='Q': # Check if we are not at end of measurement
             #print(f'Fetched the following data: {result}')
             
             # This code determines what to plot. Specifically, it 
             # concatenates the old data ith the new data from the queue
             datastream.append(result)
             timestream.append(time.time()-start_time)
             
             # Calculate the new axes
             ax.set_xlim([0,np.max(timestream)+0.1]) # 0.1 to add border
             ax.set_ylim([0,np.max(datastream)+0.1])
             
             # This code does the plotting
             line.set_data(timestream,datastream)
             ax.draw_artist(line)
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
    DELAY = 0.5
    
    # Set up arduino.
    import pyfirmata
    arduino = pyfirmata.ArduinoNano('COM5')
    time.sleep(1)
    it = pyfirmata.util.Iterator(arduino)
    it.start()
    ai = arduino.get_pin('a:0:i')
    
    # Check whether the current value of the flag that determines whether or 
    # not we should be measuring and passing those measurements on to the plot
    flag = 0
    i = 0
    while True:
        time.sleep(1)
        try:
            flag = flag_running.get_nowait()
        except:
            print("No flag") # Dummy code
        
        # If the flag setting is 1 measure and send one in three measurements
        # to the plotter.
        if flag == 1:
            data = ai.read() * 5
        
            if (not i % INTERVAL):
                q.put(data)
                
        # If the flag is set to 2 then the thread will be shutting down
        # shortly. To prepare for this, close the serial connection with the 
        # Arduino. If we do not do this, we cannot open the port next time we
        # run the code. 
        if flag == 2:
            arduino.sp.close()
            
        i += 1
    q.put('Q') # Signifies end of measurement.
   
if __name__ == '__main__':
    main()
