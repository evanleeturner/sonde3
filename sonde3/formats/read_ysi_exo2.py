import pandas as pd
from datetime import datetime
import pytz
import os
import io, itertools
import csv
import sys
import warnings
import six
import pytz
from .utils import match_param



csv.field_size_limit(sys.maxsize)

def read_ysi_exo2_csv(ysi_file,delim=','):
    """
    Method reads a text based YSI sonde instrument file in KOR >2.0 EXO format and returns a pandas DataFrame for the table and metadata.

    Method makes many assumptions about the standard formatting of the text file.
    Method assumes the file is of YSI origin, has at least two columns.

    A separator must be passed to the function as the deliminator YSI uses
    can be different.  (Somtimes tab separated, comma, or a series of spaces)

    The function assumes that ['date','time','fractime'] are in column 0 and 1 and 2.
    """
    package_directory = os.path.dirname(os.path.abspath(__file__))
    DEFINITIONS = pd.read_csv(os.path.join(package_directory,'..',"data/definitions.csv"), encoding='cp1252')

    utc=pytz.utc


    #localtime = pytz.timezone('US/Central')

    if not isinstance(ysi_file, six.string_types):
        ysi_file.seek(0)
    #grab 30 lines discover what the real header is, then trim the file
    #grab 30 lines discover what the real header is, then trim the file

    #since the YSI EXO2 files contain NULL bytes lets strip those out and just return as a string isntead:
    ysi_file = ysi_file.read().decode('ISO-8859-1')

    for line in ysi_file:
        line.replace('\0','')

    #These files no longer contain very meaninful metdata - worth the effort to parse the unstructured
    #string without making pandas go crazy.


    #raw_metadata = pd.read_csv(io.StringIO(ysi_file), sep=delim,header=None, nrows=5)
    #header_row_index = raw_metadata.loc[raw_metadata[0].str.contains("Date")==True].index[0]
    header_row_index = 8
    #raw_metadata = raw_metadata.drop(raw_metadata.index[(header_row_index-2):])
    #grab main file from header point, squash datetime row

    DF = pd.read_csv(io.StringIO(ysi_file), engine='python', parse_dates={'Datetime_(Native)': [0,1]}, sep=delim,na_values=[''],   header = header_row_index, encoding='utf-8')
    DF = DF.drop(DF.index[:header_row_index])
    DF = DF.drop('Time (Fract. Sec)',1)
    #now lets drop any rows that have bad data - this occurs when the sonde restarts
    DF = DF[DF['Datetime_(Native)'] != ' ']
    DF = DF[DF['Datetime_(Native)'] != None]
    DF = DF[DF['Datetime_(Native)'] != "Date (MM/DD/YYYY) Time (HH:mm:ss)"]
    #pd.set_option('display.max_rows', None)
    #print (DF['Datetime_(Native)'])
    #DF['Datetime_(UTC)'] = DF['Datetime_(UTC)'].values.astype('datetime64[s]')

    metadata = pd.DataFrame(columns=('Manufacturer', 'Instrument_Serial_Number', 'Sensor_Serial_Numbers', 'Model','Station','Deployment_Setup_Time', \
                                     'Deployment_Start_Time', 'Deployment_Stop_Time','Filename','User','Averaging','Firmware', 'Sensor_Firmware'))

    DF['Datetime_(Native)'] = pd.to_datetime(DF['Datetime_(Native)'])
    localtime = pytz.timezone('US/Central')
    DF.insert(0,'Datetime_(UTC)' ,  DF['Datetime_(Native)'].map(lambda x: localtime.localize(x).astimezone(utc)))
    DF = DF.drop('Datetime_(Native)', 1)
    DF = DF.drop(['Site Name'], axis=1)


    #this method strips out the crazy binary in the columns
    newcols = []
    stripped = lambda s: "".join(i for i in s if 31 < ord(i) < 127)
    for k in DF.columns:
        newcols.append(stripped(k))

    DF.columns = newcols

    DF = match_param(DF,DEFINITIONS)
    #now convert all data rows to floats...
    #move this to separate function if I have to do this more than for hydrotechs
    floater = lambda x: float(x)

    #split set
    dt_column = DF.iloc[:,0]
    data = DF.iloc[:,1:]
    data = data.applymap(floater)

    DF = pd.concat([dt_column,data], axis=1)

    return metadata, DF
