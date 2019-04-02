
"""
Script to process all files and save the VDC and peak-to-peak
voltages to a csv file.

Author: Felipe Aristizabal, Ph.D.
Date: April 1st, 2019

"""

import glob
import numpy as np
import data_read

files = glob.glob('data/VDC_*')
files.sort()

out = list()
for cf in files:
    print(cf)

    # Get V_DC value from file name
    vdc = float(cf[9:12])

    # Read data - use average only
    d = data_read.OscData(cf)

    # Calculate peak-to-peak voltage
    npts = 1000             # Number of initial points for V bias estimation
    ch1 = d.avg(ch=1)                           # Negative channel
    Vneg = -(ch1.val - np.mean(ch1.val[:npts])) # Remove bias
    ch4 = d.avg(ch=4)                           # Positive channel
    Vpos = ch4.val - np.mean(ch4.val[:npts])    # Remove bias
    pkpk = np.max(Vpos - Vneg)
    out.append([vdc, pkpk])

# Organize output and export to csv
out = np.array(out)
np.savetxt('vdc_peak.csv', out.astype(np.int),
           fmt='%i, %i',
           delimiter=',',
           header='VDC, PkPk')

