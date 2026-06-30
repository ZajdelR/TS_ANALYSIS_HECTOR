#!/usr/bin/env python3
# 
# Get all station names from directory ./raw_files and find for each one
# offsets in the time series.
#
#  This script is part of Hector 2.1
#
#  Hector is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  any later version.
#
#  Hector is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Hector.  If not, see <http://www.gnu.org/licenses/>
#
# 29/ 3/2020  Machiel Bos, Santa Clara
# 29/11/2021  Machiel Bos, Santa Clara
#===============================================================================

import sys
import os
import re
import glob
import argparse

#===============================================================================
# Main program
#===============================================================================

#--- Parse command line arguments in a bit more professional way
parser = argparse.ArgumentParser(description=\
                         'For each file in ./raw_files find the offsets')

#--- List arguments that can be given 
parser.add_argument('-p', dest='penalty', action='store', default=4.0,
       required=False, help="Extra penalty value to add to BIC_c")
parser.add_argument('-threeD', action='store_true',
       required=False, help="process east, north and up at same time")
parser.add_argument('-n', dest='noisemodels', action='store', default='PLWN',
       required=False, help="noisemodel combination (PLWN, FL, etc.)")

args = parser.parse_args()

#--- parse command-line arguments
use_3D = args.threeD
extra_penalty = float(args.penalty)
noisemodels = args.noisemodels


#--- Open files to store estimated offset times
fp_bic_c = open("offsets_BIC_c.dat","w")

#--- Retrieve all station names that need to be processed
if use_3D==True:
    fnames = glob.glob("./raw_files/*_0.mom")
else:
    fnames = glob.glob("./raw_files/*.mom")

#--- Sanity check
if len(fnames) == 0:
    print("Did not found any mom-files in the ./raw_files directory")
    sys.exit()

#--- Does the obs_files directory exists?
if not os.path.exists('./obs_files'):
    os.mkdir('./obs_files')

#--- Process each file
for fname in sorted(fnames):
    if use_3D==True:
        m = re.search("/(\w+)_\d+.mom",fname)
        if m:
            name = m.group(1)
        else:
            print('Could not find station name in {0:s}'.format(fname))
            sys.exit()
    else:
        m = re.search("/(\w+).mom",fname)
        if m:
            name = m.group(1)
        else:
            print('Could not find station name in {0:s}'.format(fname))
            sys.exit()


    #--- Check percentage missing data
    fp = open(fname,'r')
    lines = fp.readlines()
    fp.close()
    m = re.search('# sampling period (\d+\.d*)',lines[0])
    if m:
        dt = float(m.group(1))
    else:
        print('assuming daily observations')
        dt = 1.0
    i0 = 0
    while lines[i0].startswith('#')==True:
        i0 += 1
    i1   = len(lines)-1
    cols = lines[i0].split()
    t0   = float(cols[0])
    cols = lines[i1].split()
    t1   = float(cols[0])
    n    = int((t1-t0)/dt+1.0e-6)

    #--- Only for time series with n>0
    if n>0:
        percentage = 100 - (i1-i0)/n*100
    
        print('{0:s} :  {1:6.2f}%'.format(name,percentage))

        #--- If there are too many gaps, simply copy files to ./obs_files
        if percentage>40.0:
            for comp in range(0,3):
                os.system('cp -f ./raw_files/{0:s}_{1:d}.mom ./obs_files/'. \
							     format(name,comp))

        #--- Else, run find_offset.py
        else:
            if use_3D==True:
                status = os.system("find_offset.py {0:s} {1:s} 3D {2:f}". \
				      format(name,noisemodels,extra_penalty))
            else:
                status = os.system("find_offset.py {0:s} {1:s} {2:f}". \
				      format(name,noisemodels,extra_penalty))
            with open("findoffset_BIC_c.dat",'r') as fp_in:
                for line in fp_in:
                    fp_bic_c.write("{0:12s}  {1:s}\n".\
						format(name,line.rstrip()))

fp_bic_c.close()
