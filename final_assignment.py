# -*- coding: utf-8 -*-
"""
Created on Wed Jan 20 20:00:29 2021
@author: thijn
"""

from random import random
import tables 
import numpy as np

filename='measurement.h5'

# https://stackoverflow.com/questions/30376581/save-numpy-array-in-append-mode
COLUMNS = 2
WINDOW_SIZE = 20

f = tables.open_file(filename, mode='w')
atom = tables.Float64Atom()

array_c = f.create_earray(f.root, 'data', atom, (0, COLUMNS))

import tkinter as tk
import threading

import time
    
flag_running = False   
flag_exiting = False   
  
root = tk.Tk()
    
# global filename
# filename=r'C:\Users\Public\data.npz'
import matplotlib.pyplot as plt
plt.close('all') # need to close previous plots before running this code. Otherwise kernel crashes

from IPython.display import clear_output


# this part of the code contains the acquisition

def measure():  
     
    plt.close('all')
    global flag_running    
    global flag_exiting  
    global filename
    global f
    global array_c
   
    import pyfirmata

    start = time.time()
    global COLUMNS
    global WINDOW_SIZE
    
    window = np.zeros((WINDOW_SIZE,2))
    
    small_delay=0.1 # brief time to wait, such that program can execute, 
    # also longer than 1 ms to avoid crosstalk between channels
    long_delay=1# longer time to wait, determines how often a measurement is taken. 


    try:
       
        while ( True ):  
            if (flag_running == True):    # as long as the flag is high: acquire, else pause
                clear_output(wait=True)
                
                time.sleep(1)
                data = random()
                timepoint = time.time()-start
                x = [[timepoint, data]]
                array_c.append(x)
                
                window = np.roll(window, -1, axis=0)
                window[-1,:]=[timepoint,data]
               
                print(window)
             
                time.sleep(0.1)
                

            if (flag_exiting == True):   # check whether to stop
                time.sleep(small_delay)
                return   
            
            time.sleep(small_delay)
            
        time.sleep(small_delay)
    except KeyboardInterrupt:   
        pass  

# the following code checks whether buttons are pushed, if so a flag is set        
def switchon():      
    global flag_running    
    flag_running = True    
    print ('flag_running on'   )  
          
def switchoff():      
    global flag_running   
    flag_running = False        
    print ('flag_running off'  )  
          
def kill():   
    global flag_exiting     
    flag_exiting = True  
    root.destroy()      

          
thread = threading.Thread(target=measure)    
thread.start()    
  
onbutton = tk.Button(root, text = "Starting ON", command = switchon)      
onbutton.pack()      
offbutton =  tk.Button(root, text = "Postponing OFF", command = switchoff)      
offbutton.pack()      
killbutton = tk.Button(root, text = "EXIT", command = kill)      
killbutton.pack()      
    
root.mainloop() 
time.sleep(1)
f.close()
print('closed')

time.sleep(.5)

f = tables.open_file(filename, mode='r')
print('opened')
print(f.root.data[-4:,:]) # e.g. read from disk only this part of the dataset

time.sleep(1)
f.close()

clear_output(wait=True)

print('closed')

#tables.file._open_files.close_all()
