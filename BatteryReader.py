import sys
import time
import subprocess as sp
import numpy as np
import pandas as pd
from datetime import datetime
from AppKit import NSWorkspace




# this program runs by parsing the output of the "top" command.
# The raw output of the command is saved to a .txt, the script runs the txt, refactors data, then saves to a CSV
# CPU total usage has PID -10, and current battery status has PID -20

# CURRENT ISSUES / TO DO
# storing raw output in a txt file is probably unnecessary, but I couldnt find a workaround
# I am unsure what state does
# note, the first set of data output by top is always faulty
# AppKit .activeApplication() is depreciated. Newer functions don't have the same functionality
# Train a machine learning algorithm that takes CSV as an input and closes offending apps to save battery
# Android adaptive battery (the inspiration for this project) takes historic charging times into account to predict how long your battery needs to last and throttles apps accordingly
# closing apps is easy, limiting CPU is more difficult. Still possible though, https://github.com/AppPolice/AppPolice
# Have not delt with child programs, unsure how to prevent them / add their CPU usage to their parent app.
# storing app names in the CSV improves readability, but increases file size and is unnecessary to train an ML model. Should be removed in the final version 

TIMES = 5  # how many data samples to collect
DELAY = 5  # how long in seconds between collecting samples
TEMP_TXT_ADDRESS = "/Users/patrickhardison/Desktop/DAML/file.txt"
OUTPUT_CSV_ADDRESS = '/Users/patrickhardison/Desktop/DAML/output.csv'


# loops a readline until a new output appears
def waitForResponse(var,dict):
    waitclock = 0
    interval = datetime.now()
    while True:
        test = var.readline()
        if (test != ''):
            return test
        pid = NSWorkspace.sharedWorkspace().activeApplication()["NSApplicationProcessIdentifier"]
        dict.update({int(pid):datetime.now()})
        time.sleep(5)
    


def main():

   

    # get active user's name
    username = sp.Popen("id -un", text=True, shell=True, stdout=sp.PIPE)
    out, err = username.communicate()
    time.sleep(1)
    print(out)

    


    # clear the text file
    clearcmd = [f'echo "" > {TEMP_TXT_ADDRESS}']
    sp.Popen(clearcmd, shell=True)
    time.sleep(2)


    # Create dataframe
    df = pd.DataFrame(columns=["Usage", "status", "name", "time", "PID", "Last Opened"])
    df = df.set_index(["time", "PID"])
    print(df)

    # begin gathering data
    cmd = [f'top -l  {str(TIMES+1)}  -s {str(DELAY)} -n 10 -stats pid,cpu,state,command -U {str(out[0:-1])} > {TEMP_TXT_ADDRESS} &']
    results = sp.Popen(cmd, text=True, shell=True, stdout=sp.PIPE, stderr=sp.PIPE)


    f = open(TEMP_TXT_ADDRESS, "r")
    time.sleep(2)
    
    # (PID, DateTime of last open)
    lastopened = {}

    for rep in range(TIMES):
        
        
        # boilerplate: save or discard data that appears before app data
        boilerplate = []
        print(lastopened)

        # wait for response function handles time between data coming in
        # Also checks for active window and updates the lastopened dict        
        boilerplate.append(waitForResponse(f,lastopened))
        print(lastopened)

        for n in range(9):
            boilerplate.append(f.readline())

        discard = f.readline()
        discard = f.readline()

        cpuTotal = boilerplate[3].split(" ")[2][0:-1]
        print(boilerplate[3] + "\n")
        print(cpuTotal)

        # gather info on running apps. data variable is a 2d array
        data = []
        for n in range(10):
            appdata = f.readline()
            appdata = appdata[0:len(appdata)-1]
            appdata = appdata.split(None, 3)
            appdata[3] = appdata[3].strip()
            appdata = [i for i in appdata if i]
            if appdata[0][-1] == "*": appdata[0] = appdata[0][0:-1] #remove random asterisk on PID column?
            data.append(appdata)
            #print(appdata)

        # skip the first iteration, returns faulty data
        if rep == 0:
            continue

        Time = boilerplate[1][0:-1]
        dTime = datetime.strptime(Time, '%Y/%m/%d %H:%M:%S')

        # Add data to pandas dataframe
        for x in data:
            x.append(dTime)

            #Calculate elapsed time based on lastopened dictionary, default to -1, pop after 20 minutes to save memory
            if int(x[0]) in lastopened.keys():
                elapsed = int((dTime - lastopened[int(x[0])]).total_seconds())
                print(elapsed)
                if elapsed > 600: 
                    lastopened.pop(int(x[0]))
                    lasttime = None
                else: lasttime = elapsed
            else: lasttime = None
            df.loc[(x[4], int(x[0])), :] = [x[1], x[2], x[3], lasttime]

        # run command to collect battery data and save to dataframe.
        battCMD = sp.Popen("pmset -g batt", text=True,shell=True, stdout=sp.PIPE)
        battout, err = battCMD.communicate()

        battdata = battout.split("\t")[1].split("; ")
        df.loc[(dTime, -20), :] = [battdata[0][0:-1], battdata[1], "BATTERY INFO", "N/A"]


        # add total CPU usage to dataframe
        df.loc[(dTime, -10), :] = [cpuTotal, "N/A", "CPU TOTAL", "N/A"]
       
        
        

        print(df.sort_index(level=0))

        print("--------")
        # line = df.plot.line()
        # plt.plot(line)
        print("\n")


    df.to_csv(OUTPUT_CSV_ADDRESS)


if __name__ == "__main__":
    main()



