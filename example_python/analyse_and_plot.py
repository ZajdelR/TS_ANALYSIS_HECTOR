#!/usr/bin/env python3
# 
# Read all mom-files in the ./obs_files directory, analyse them, plot them
# and create power spectral density plots.
#
# The JSON file of each analysis is added to a new hector.json file. Simply
# copying the lines with some added indentation.
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
# 29/3/2020 Machiel Bos, Santa Clara
#===============================================================================

import sys
import math
import os
import argparse
import re
import glob
import json
import subprocess

#===============================================================================
# Subroutines
#===============================================================================

# Compute year, month and day from MJD
#---------------
def caldat(mjd):
#---------------
    """ Compute calendar date for given julian date.
    * 
    * Example: YEAR = 1970, MONTH = 1, DAY = 1, JD = 2440588. 
    * Reference: Fliegel, H. F. and van Flandern, T. C., Communications of 
    * the ACM, Vol. 11, No. 10 (October, 1968).
    *
    * http://www.usno.navy.mil/USNO/astronomical-applications/
    """
    jul = mjd + 2400001
    l = jul+68569;
    n = 4*l//146097;
    l = l-(146097*n+3)//4;
    i = 4000*(l+1)//1461001;
    l = l-1461*i//4+31;
    j = 80*l//2447;
    k = l-2447*j//80;
    l = j//11;
    j = j+2-12*l;
    i = 100*(n-49)+i+l;

    year  = i;
    month = j;
    day   = k;

    return [year,month,day]



# Make plot of Power-Spectrum
#-----------------------
def make_PSD_plot(name):
#-----------------------
    """ Make a power spectral density plot from the residuals 
    
    Arguments:
        name = name of station and filename without .mom extension
    """

    #--- create new gnuplot script file
    fp = open("plot_spectra.gpl", "w")
    fp.write("set terminal postscript enhanced size 4,4 color portrait" + \
                                                      " solid \"Helvetica\"\n")
    fp.write("set output './psd_figures/{0:s}_psd.ps'\n".format(name))
    fp.write("set border 3;\n")
    fp.write("set xlabel 'Frequency (cpy)' font 'Helvetica, 18';\n")
    fp.write("set ylabel 'Power (mm^2/cpy)' offset -1,0 font 'Helvetica, 18'\n")
    fp.write("set xtics nomirror;\n")
    fp.write("set xtics autofreq;\n")
    fp.write("set ytics nomirror;\n")
    fp.write("set ytics autofreq;\n")
    fp.write("set logscale xy;\n")
    fp.write("set nokey;\n")
    fp.write("set format y '10^{%T}';\n")
    fp.write("set format x '10^{%T}';\n")
    fp.write("set pointsize 1;\n")
    fp.write("set xrange[*:*];\n")
    fp.write("set yrange[*:*];\n")
    fp.write("s=31557600.0;\n")
    fp.write("set style line 1 lt 1 lw 3 pt 7 linecolor rgb \"#a6cee3\"\n")
    fp.write("set style line 2 lt 1 lw 3 pt 7 linecolor rgb \"red\"\n")
    fp.write("set style line 3 lt 1 lw 1 pt 7 linecolor rgb \"red\"\n")
    fp.write("plot 'estimatespectrum.out' using ($1*s):($2/s) w p ls 1,\\\n")
    fp.write("     'modelspectrum.out'    using ($1*s):($2/s) w l ls 2,\\\n")
    fp.write(" 'modelspectrum_percentiles.out' u ($1*s):($2/s) w l ls 3,\\\n"),\
    fp.write(" 'modelspectrum_percentiles.out' u ($1*s):($4/s) w l ls 3\n")
    fp.close()

    #--- Call gnuplot
    try:
        subprocess.call(['gnuplot','plot_spectra.gpl'])
    except OSError:
        print('Something seems to have gone wrong with the powerspectrum plot')
    os.system('gmt psconvert -Te -A0.1 ./psd_figures/{0:s}_psd.ps'.\
								format(name))
    os.system('convert -density 300 -flatten -antialias ' +  \
		'./psd_figures/{0:s}_psd.eps ./psd_figures/{0:s}.png\n'.\
								  format(name))



#------------------------
def make_data_plot(name):
#------------------------
    """ Make a time series plot

    Parameters:
        name : station name
    """  
    #--- create new gnuplot script file
    fp = open("plot_data.gpl", "w")
    fp.write("set terminal postscript enhanced size 8,4.8 color portrait" + \
                                                        " solid 'Helvetica'\n")
    fp.write("set output './data_figures/{0:s}_data.ps'\n".format(name))
    fp.write("set border 3;\n")
    fp.write("set xlabel 'Years' font 'Helvetica, 18';\n")
    fp.write("set ylabel 'mm' offset -1,0 font 'Helvetica, 18';\n")
    fp.write("set xtics nomirror;\n")
    fp.write("set xtics autofreq;\n")
    fp.write("set ytics nomirror;\n")
    fp.write("set ytics autofreq;\n")
    fp.write("set nokey;\n")
    fp.write("set pointsize 0.4;\n")
    fp.write("set bar 0.5;\n")
    fp.write("set xrange[*:*];\n")
    fp.write("set yrange[*:*];\n")
    fp.write("set style line 1 lt 1 lw 3 pt 7 linecolor rgb '#a6cee3'\n")
    fp.write("set style line 2 lt 1 lw 3 pt 7 linecolor rgb 'red'\n")
    fp.write("set style line 3 lt 1 lw 3 pt 2 linecolor rgb 'black'\n")
    fp.write("plot './mom_files/{0:s}.mom' u".format(name) + \
                                " (($1-51544)/365.25+2000):2 w p ls 1,\\\n")
    fp.write("     './mom_files/{0:s}.mom' u".format(name) + \
                                " (($1-51544)/365.25+2000):3 w l ls 2")
    fp.write("\n")

    #---- A plot of the residuals is also nice to have
    fp.write("\nset output './data_figures/{0:s}_res.eps'\n".format(name))
    fp.write("plot './mom_files/{0:s}.mom' u ".format(name) + \
                                " (($1-51544)/365.25+2000):($2-$3) w l ls 2\n")
    fp.close()

    #--- Call gnuplot
    os.system('gnuplot plot_data.gpl')
   
    os.system('gmt psconvert -Te -A0.1 ./data_figures/{0:s}_data.ps'.\
								format(name))
    os.system('convert -density 300 -flatten -antialias ' +  \
	'./data_figures/{0:s}_data.eps ./data_figures/{0:s}.png\n'.\
								format(name))
 

#===============================================================================
# Main program
#===============================================================================

#--- Parse command line arguments in a bit more professional way
parser = argparse.ArgumentParser(description= 'Estimate trend')

#--- List arguments that can be given
parser.add_argument('-s', required=False, dest='station', \
                              default="", help='station name')
parser.add_argument('-n', required=True, dest='noisemodel', \
                                        help='noise model labels')
parser.add_argument('-f', required=False, dest='freq', \
                                      default='0.0', help='extra frequency')

args = parser.parse_args()

#--- parse command-line arguments
station    = args.station
noisemodel = args.noisemodel
freq       = float(args.freq)


if station=="":    
    stations = []
    #--- Read station names in directory ./obs_files
    fnames = glob.glob("./obs_files/*.mom")
    
    #--- Did we find files?
    if len(fnames)==0:
        print('Could not find any mom-file in ./obs_files')
        sys.exit()

    #--- Extract station names
    for fname in sorted(fnames):
        m = re.search('/(\w+)\.mom',fname)
        if m:
            station = m.group(1)
            stations.append(station)
        else:
            print('Could not parse station name from: {0:s}'.format(fname))
            sys.exit()
else:
    stations = [station]

#-- Open new JSON file to store all other JSON results
fp_json_est = open('hector_estimatetrend.json','w')
fp_json_est.write('{')
fp_json_rem = open('hector_removeoutliers.json','w')
fp_json_rem.write('{')

#--- Store outliers in dictionary
outliers = {}

#--- Analyse station
for station in stations:

    #--- Get sampling period
    try:
        fp_mom = open("./obs_files/{0:s}.mom".format(station))
    except IOError:
        print("Could not open file ./obs_files/{0:s}.mom".format(station))
        sys.exit()

    lines = fp_mom.readlines()
    m = re.search('# sampling period (\d+\.?\d*)',lines[0])
    if m:
        sampling_period = float(m.group(1))
        fs = 1.0/float(m.group(1))
        T = 1.0/(365.25*fs)
    else:
        print("./obs_files/{0:s}.mom does not have # sampling period!". \
								format(station))
        sys.exit()

    #--- Get first and last observation epoch
    i =0
    n = len(lines)
    while lines[i].startswith('#')==True and i<n:
        i += 1
    cols = lines[i].split()  
    mjd0 = float(cols[0])
    cols = lines[n-1].split()  
    mjd1 = float(cols[0])
    n    = int((mjd1-mjd0)/sampling_period + 1.0e-6)
    print(mjd0,mjd1,sampling_period,n)

    #--- Get 4 letter marker and component
    m = re.search('(\w+)_(\d)',station)
    if m:
        marker    = m.group(1)
        component = m.group(2)
    else:
        marker    = station
        component = None

    if freq>0.0:
        param = '-s {0:s} -n {1:s} -f {2:f}'.format(station,noisemodel,freq)
    else:
        param = '-s {0:s} -n {1:s}'.format(station,noisemodel)
    print('#### {0:s}'.format(param))
    os.system('analyse_timeseries.py {0:s}'.format(param))
    fp_dummy = open('estimatetrend.json','r')
    results = json.load(fp_dummy)
    fp_dummy.close()
 
    #--- Does the data_figures directory exists?
    if not os.path.exists('./data_figures'):
        os.mkdir('./data_figures')

    #--- Does the psd_figures directory exists?
    if not os.path.exists('./psd_figures'):
        os.mkdir('./psd_figures')

    #--- Create control file to estimate power spectrum of residuals
    fp = open("estimatespectrum.ctl", "w")
    fp.write("DataFile            {0:s}.mom\n".format(station))
    fp.write("DataDirectory       ./mom_files\n")
    fp.write("interpolate         no\n")
    fp.write("NoiseModels         {0:s}\n".format(noisemodel))
    fp.write("ScaleFactor         1.0\n")
    fp.write("PhysicalUnit        mm\n")
    fp.write("WindowFunction      Hann\n")
    fp.close()

    #--- Run estimatespectrum
    output = subprocess.check_output('estimatespectrum 4',shell=True) 
    estimatespectrum_cols = output.decode().split()
    freq0 = estimatespectrum_cols[-5]
    freq1 = estimatespectrum_cols[-3]

    #--- Read estimatetrend.ctl for details about GGM_1mphi, lamba_fixed,
    #    phi_fixed.
    GGM_1mphi_needed = True
    lambda_needed = True
    kappa_needed = True
    with open('estimatetrend.ctl','r') as fp:
        for line in fp:
            m = re.match('GGM_1mphi',line)
            if m:
                GGM_1mphi_needed = False
                cols = line.split()
                GGM_1mphi = float(cols[1])
            m = re.match('kappa_fixed',line)
            if m:
                kappa_needed = False
                cols = line.split()
                kappa_fixed = float(cols[1])
            m = re.match('lambda_fixed',line)
            if m:
                lambda_needed = False
                cols = line.split()
                lambda_fixed = float(cols[1])

    #--- Create control file for modelspectrum
    fp = open("modelspectrum.ctl","w")
    fp.write("DataFile                {0:s}.mom\n".format(station))
    fp.write("DataDirectory           ./mom_files\n")
    fp.write("ScaleFactor             1.0\n")
    fp.write("PhysicalUnit            mm\n")
    noise_lst = ''
    noises = results['NoiseModel']
    for noise in noises:
        noise_lst += ' ' + noise

    if GGM_1mphi_needed==False:
        fp.write("GGM_1mphi             {0:e}\n".format(GGM_1mphi))
    if kappa_needed==False:
        fp.write("kappa_fixed           {0:f}\n".format(kappa_fixed))
    if lambda_needed==False:
        fp.write("lambda_fixed          {0:e}\n".format(lambda_fixed))

    fp.write("NoiseModels            {0:s}\n".format(noise_lst))
    fp.write("AR_p                    1\n")
    fp.write("MA_q                    0\n")
    fp.write("TimeNoiseStart          1000\n")
    fp.write("MonteCarloConfidence    yes\n")
    fp.write("NumberOfSimulations     5000\n")
    fp.write("SamplingPeriod          {0:f}\n".format(sampling_period))
    fp.write("NumberOfPoints          {0:d}\n".format(n))
    fp.write("NumberOfSegments        4\n")
    fp.write("WindowFunction          Hann\n")
    fp.close()

    #--- Create input for modelspectrum
    fp = open("modelspectrum.txt","w")
    sigma = results['driving_noise']
    fp.write("{0:f}\n{1:f}\n".format(sigma,24.0/fs))
    #--- Select NoiseModel section from json structure
    noises = results['NoiseModel']

    #--- First, enter all the fractions
    for model in noises.keys():
        noise = noises[model]
        fp.write("{0:f}\n".format(noise['fraction']))

    #--- Secondly, enter specific noise parameters
    #    Nothing to add for White, FlickerGGM or RandomWalkGGM
    for model in noises.keys():
        noise = noises[model]
        if model=='GGM':
            d = noise['d']
            if kappa_needed==True:
                fp.write('{0:f}\n'.format(d))
            if GGM_1mphi_needed==True:
                phi = noise['1-phi']
                fp.write('{0:f}\n'.format(phi))
        elif model=='Powerlaw' or model=='PowerlawApprox':
            d = noise['d']
            fp.write('{0:f}\n'.format(d))
        elif model=='VaryingAnnual' or model=='VaryingSemiAnnual':
            phi = noise['phi']
            fp.write('{0:f}\n'.format(phi))
        elif model=='Matern':
            if kappa_needed==True:
                d = noise['d']
                fp.write('{0:f}\n'.format(d))
            if lambda_needed==True:
                lambda_ = noise['lambda']
                fp.write('{0:f}\n'.format(lambda_))
        elif model=='ARMA':
            phi = noise['AR'][0]
            fp.write('{0:f}\n'.format(phi))

    #--- Finally, write information about lowest and highest frequency
    fp.write("2\n{0:s} {1:s}\n".format(freq0,freq1))
    fp.close()

    #--- Make modelled psd line
    os.system('modelspectrum < modelspectrum.txt > /dev/null')

    #--- Make plot of power-spectrum and data
    make_PSD_plot(station)

    #--- Make time series plot
    make_data_plot(station)

    #--- update json file
    if station!=stations[0]:
        fp_json_est.write(',')
        fp_json_rem.write(',')
    fp_json_est.write('\n  "{0:s}" : {{\n'.format(station))
    fp_json_rem.write('\n  "{0:s}" : {{\n'.format(station))
    fp_dummy = open('estimatetrend.json','r')
    lines = fp_dummy.readlines()
    fp_dummy.close()
    for i in range(1,len(lines)-1):
        fp_json_est.write('  ' + lines[i])
    fp_json_est.write('  ' + lines[-1].rstrip("\n"))
    fp_dummy = open('removeoutliers.json','r')
    lines = fp_dummy.readlines()
    fp_dummy.close()
    for i in range(1,len(lines)-1):
        fp_json_rem.write('  ' + lines[i])
    fp_json_rem.write('  ' + lines[-1].rstrip("\n"))


fp_json_est.write('\n}\n')        
fp_json_est.close()
fp_json_rem.write('\n}\n')        
fp_json_rem.close()
