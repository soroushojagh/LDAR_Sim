# ------------------------------------------------------------------------------
# Program:     The LDAR Simulator (LDAR-Sim) 
# File:        LDAR-Sim main
# Purpose:     Interface for parameterizing and running LDAR-Sim.
#
# Copyright (C) 2018-2020  Thomas Fox, Mozhou Gao, Thomas Barchyn, Chris Hugenholtz
#    
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, version 3.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# ------------------------------------------------------------------------------

from batch_reporting import *
from ldar_sim_run import *
import os
import datetime
import warnings
import multiprocessing as mp
import boto3 # for downloading data from AWS

if __name__ == '__main__':
    # ------------------------------------------------------------------------------
    # -----------------------------Global parameters--------------------------------
    wd = "../inputs_template/"
    
    #-------------------------------------------------------------------------------
    #------------------------------Check ERA5 data in the working directory---------    
    check_ERA5_file(wd,"AB") # AB stands for Alberta 

    program_list = ['P_ref','P_alt', 'P_alt2', 'P_cont']  # Programs to compare; Position one should be the reference program (P_ref)

    # -----------------------------Set up programs----------------------------------
    programs = []
    wd = os.path.abspath (wd) + "/"
    warnings.filterwarnings('ignore')    # Temporarily mute warnings
    

    for p in range(len(program_list)):
        file = wd + program_list[p] + '.txt'
        exec(open(file).read())
        programs.append(eval(program_list[p]))

    n_processes = programs[0]['n_processes']
    print_from_simulations = programs[0]['print_from_simulations']
    n_simulations = programs[0]['n_simulations']
    spin_up = programs[0]['spin_up']
    ref_program = program_list[0]
    write_data = programs[0]['write_data']
    output_directory = wd + 'outputs/'

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Set up simulation parameter files
    simulations = []
    for i in range(n_simulations):
        for j in range(len(programs)):
            opening_message = 'Simulating program ' + str(j + 1) + ' of ' + str(len(programs)) + '; simulation ' + \
                                str(i + 1) + ' of ' + str(n_simulations)
            simulations.append([{'i': i, 'program': programs[j], 'wd': wd, 'opening_message': opening_message,
                                'print_from_simulation': print_from_simulations}])

    # Perform simulations in parallel
    with mp.Pool(processes=n_processes) as p:
        res = p.starmap(ldar_sim_run, simulations)

    # Do batch reporting
    if write_data:
        # Create a data object...
        reporting_data = BatchReporting(output_directory, programs[0]['start_year'], spin_up, ref_program)
        if n_simulations > 1:
            reporting_data.program_report()
            if len(programs) > 1:
                reporting_data.batch_report()
                reporting_data.batch_plots()

    # Write metadata
    metadata = open(output_directory + '/metadata.txt', 'w')
    metadata.write(str(programs) + '\n' +
                   str(datetime.datetime.now()))

    metadata.close()

    # Write sensitivity analysis data on a program by program basis
    sa_df = pd.DataFrame(res)
    if 'program' in sa_df.columns:
        for program in sa_df['program'].unique():
            sa_out = sa_df.loc[sa_df['program'] == program, :]
            sa_outfile_name = os.path.join(wd, 'sensitivity_analysis', 'sensitivity_' + program + '.csv')
            sa_out.to_csv(sa_outfile_name, index=False)

