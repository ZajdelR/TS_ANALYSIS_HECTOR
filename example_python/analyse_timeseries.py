#!/usr/bin/env python3
# 
# For given mom-filename and noise model combination, analyse the time series.
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
#===============================================================================

import sys
import os
import re
import argparse

#===============================================================================
# Subroutines
#===============================================================================


#------------------------------------------------
def create_removeoutliers_ctl_file(station,freq):
#------------------------------------------------
    """ Create ctl file for removeoutlier.

    Args:
        station : station name (including _0, _1 or _2) of the mom-file
    """

    #--- Create control.txt file for removeoutliers
    fp = open("removeoutliers.ctl", "w")
    fp.write("DataFile            {0:s}.mom\n".format(station))
    fp.write("DataDirectory         ./obs_files\n")
    fp.write("interpolate           no\n")
    fp.write("OutputFile            ./pre_files/{0:s}.mom\n".format(station))
    fp.write("seasonalsignal        yes\n")
    fp.write("halfseasonalsignal    yes\n")
    if freq>0.0: 
        fp.write("periodicsignals       {0:f}\n".format(freq))
    fp.write("estimateoffsets       yes\n")
    fp.write("estimatepostseismic   yes\n")
    fp.write("estimateslowslipevent yes\n")
    fp.write("ScaleFactor           1.0\n")
    fp.write("PhysicalUnit          mm\n")
    fp.write("IQ_factor             3\n")
    fp.write("JSON                  yes\n")
    fp.close()



#-------------------------------------
def parse_noisemodels(noisemodel_abr):
#-------------------------------------
    """ Convert string of abbreviations into list of noise models

    Args:
        noisemodel_str (string) : noisemodels written as one string
    """

    abbreviations = ['fGGM','MT','GGM','PL','FN','WN','RW','AR1','VA','VSA']

    i0=0
    i1=2
    noisemodels = []
    n = len(noisemodel_abr)
    while i1<=n:
        try :
            index = abbreviations.index(noisemodel_abr[i0:i1])
        except ValueError : 
            index = -1
        while index<0 and i1<=n and i1-i0<4:
            i1 += 1
            try :
                index = abbreviations.index(noisemodel_abr[i0:i1])
            except ValueError : 
                index = -1
        if index<0:
            print('Unknown abbreviation: {0:s}'.format(noisemodel_abr[i0:i1]))
            sys.exit()
        else:
            if noisemodel_abr[i0:i1] in noisemodels:
                print('{0:s} repeated!'.format(noisemodel_abr[i0:i1]))
                sys.exit()
            noisemodels.append(noisemodel_abr[i0:i1])
            i0 = i1
            i1 += 2
         
    #--- Sanity check
    if ('GGM' in noisemodels) and ('PL' in noisemodels or 'FN' in noisemodels \
						       or 'RW' in noisemodels): 
        print('Cannot have GGM and one of the PL|FN|RW noise models')
        sys.exit()

    return noisemodels


 
#------------------------------------------------------------
def create_estimatetrend_ctl_file (station,noisemodels,freq):
#------------------------------------------------------------
    """ Create ctl file for findoffset.

    Args:
        station : station name (including _0, _1 or _2) of the mom-file
        noisemodels (list): ['GGM','PL','WN',...]
    """

    #--- Create control.txt file for EstimateTrend
    fp = open("estimatetrend.ctl", "w")
    fp.write("DataFile              {0:s}.mom\n".format(station))
    fp.write("DataDirectory         ./pre_files\n")
    fp.write("OutputFile            ./mom_files/{0:s}.mom\n".format(station))
    fp.write("interpolate           no\n")
    fp.write("PhysicalUnit          mm\n")
    fp.write("ScaleFactor           1.0\n")
    fp.write("JSON                  yes\n")
    names = ''
    need_1mphi = False
    need_varying_phi = False
    for noisemodel in noisemodels:
        if noisemodel=='WN':
            names += ' White'
        elif noisemodel == 'GGM' or noisemodel == 'fGGM':
            names += ' GGM'
        elif noisemodel == 'FN':
            names += ' FlickerGGM'
            need_1mphi = True
        elif noisemodel == 'RW':
            names += ' RandomWalkGGM'
            need_1mphi = True
        elif noisemodel == 'PL':
            names += ' GGM'
            need_1mphi = True
        elif noisemodel == 'MT':
            names += ' Matern'
        elif noisemodel == 'VA':
            names += ' VaryingAnnual'
            need_varying_phi = True
        elif noisemodel == 'VSA':
            names += ' VaryingSemiAnnual'
            need_varying_phi = True
        elif noisemodel == 'AR1':
            names += ' ARMA'
            fp.write("AR_p                  1\n")
            fp.write("MA_q                  0\n")

    fp.write("NoiseModels           {0:s}\n".format(names.lstrip()))
    
    if need_1mphi == True:
        fp.write("GGM_1mphi             6.9e-06\n")
    if need_varying_phi == True:
        fp.write("phi_varying_fixed     0.9999\n")
    if 'fGGM' in noisemodels:
        fp.write("GGM_1mphi             0.02\n")
        fp.write("kappa_fixed           -1.0\n")

    fp.write("seasonalsignal        yes\n")
    fp.write("halfseasonalsignal    yes\n")
    if freq>0.0: 
        fp.write("periodicsignals       {0:f}\n".format(freq))
    fp.write("estimateoffsets       yes\n")
    fp.write("estimatepostseismic   yes\n")
    fp.write("estimateslowslipevent yes\n")
    fp.write("ScaleFactor           1.0\n")
    fp.write("PhysicalUnit          mm\n")
    fp.close()



#===============================================================================
# Main program
#===============================================================================


#--- Parse command line arguments in a bit more professional way
parser = argparse.ArgumentParser(description= 'Estimate trend')

#--- List arguments that can be given
parser.add_argument('-s', required=True, dest='station', \
                                        help='station name')
parser.add_argument('-n', required=True, dest='noisemodel_abr', \
                                        help='noise model labels')
parser.add_argument('-f', required=False, dest='freq', \
                                      default='0.0', help='extra frequency')

args = parser.parse_args()

#--- parse command-line arguments
station        = args.station
noisemodel_abr = args.noisemodel_abr
freq           = float(args.freq)


#--- Check if the file exists 
if os.path.isfile("./obs_files/{0:s}.mom".format(station))==False:
     print("Cannot find {0:s}.mom file in obs_files directory".format(station))
     sys.exit()

#--- Does the mom-directory exists?
if not os.path.exists('./pre_files'):
     os.makedirs('./pre_files')

#--- Does the mom-directory exists?
if not os.path.exists('./mom_files'):
     os.makedirs('./mom_files')

#--- Remove outliers    
create_removeoutliers_ctl_file(station,freq)
os.system("removeoutliers > removeoutliers.out")

#--- Run estimatetrend
noisemodels = parse_noisemodels(noisemodel_abr)
create_estimatetrend_ctl_file(station,noisemodels,freq)
os.system("estimatetrend > estimatetrend.out")

