# (c) Nelen & Schuurmans. GPL licensed, see LICENSE.txt
# -*- coding: utf-8 -*-

import logging
import sys
import os
import traceback
from math import log as ln
import csv

from turtlebase.logutils import LoggingConfig
from turtlebase import mainutils
import nens.gp
import turtlebase.arcgis
import turtlebase.filenames
import turtlebase.general

logger = logging.getLogger(__name__)
EPSILON = 0.000001

def conv_gumbel_to_x(value):
    return -ln(-ln(1.0-1.0/value))
    
def calc_mean_square(l):
    '''
    #input: [[x1,y1],[x2,y2],[x3,y3],...]
    #output: alpha, beta (alpha + beta*x is the function)
    '''
    sum_x = 0.0
    sum_y = 0.0
    sum_xy = 0.0
    sum_sqr_x = 0.0
    n = len(l)
    for i in range(len(l)):
        sum_x = sum_x + l[i][0]
        sum_y = sum_y + l[i][1]
        sum_xy = sum_xy + l[i][0] * l[i][1]
        sum_sqr_x = sum_sqr_x + l[i][0] * l[i][0]
    beta = (n*sum_xy-sum_x*sum_y) / (n*sum_sqr_x - sum_x*sum_x)
    alpha = (1.0/n)*sum_y - (1.0/n)*beta*sum_x
    return alpha, beta

    
def main():
    try:
        gp = mainutils.create_geoprocessor()
        config = mainutils.read_config(__file__, 'turtle-settings.ini')
        logfile = mainutils.log_filename(config)
        logging_config = LoggingConfig(gp, logfile=logfile)
        mainutils.log_header(__name__)
        #----------------------------------------------------------------------------------------
        #check inputfields
        logger.info("Getting commandline parameters")
        try:
            input_file = sys.argv[1]
            input_prefix = sys.argv[2]
            output_file = sys.argv[3]
        except:
            logger.error("Usage: python rural_bepalen_watersysteemlijn.py [input.csv] [prefix_columnname] [output.csv]")
            sys.exit(1)

        logger.info("Reading input file...")
        csv_raw = csv.DictReader(file(input_file))

        #per id a set of coordinates will be set
        #the x value comes from columnname (they are a fixed number) in Gumbel distribution, the y value is the value in the table
        data = {}

        logger.info("Indexing input file...")
        idx_id = -1
        fields = [] #store dictionaries with 'index' and 'value'

        #indexing: find all columns and store their index
        gpgident = config.get('GENERAL', 'gpgident')

        result = {}
        logger.info("read csv")
        prefix = input_prefix
        no_value = config.get('watersysteemlijn', 'no_value')
        for row in csv_raw:
            
            if gpgident in row.keys():
                gpg_ident = row[gpgident]
                result[gpg_ident] = []
                for key in row.keys():
                    if key[:len(prefix)] == prefix:
                        ws = float(key[len(prefix):])
                        if ws > 1:
                            y = float(row[key])
                            x = conv_gumbel_to_x(ws)
                            if (abs(y - float(no_value)) > EPSILON):
                                result[gpg_ident].append([x, y])                    
            else:
                logger.error('%s not available in input csv file' % gpgident)
                sys.exit(1)

        data_output = [] #Location, beta, x0 
        calc_ok = 0
        calc_warning = 0
        for key,value in result.items():
            if len(value) > 0:
                alpha, beta = calc_mean_square(value)
                data_output.append((key, beta, alpha))
                calc_ok += 1
            else:
                logger.warning("key "+key+" does not have valid values")
                calc_warning += 1

        #print data_output
        logger.info(str(calc_ok)+" items calculated, "+str(calc_warning)+" items not calculated.")

        logger.info("Writing to output file...")
        # Add header to output csv file
        turtlebase.general.add_to_csv(output_file, [('Location','Scale par. Beta','Location par. x0')], "wb")
        for row in data_output:
            turtlebase.general.add_to_csv(output_file, [row], "ab")        
        
        mainutils.log_footer()

    except:
        logger.error(traceback.format_exc())
        sys.exit(1)

    finally:
        logging_config.cleanup()
        del gp
        
