import pandas as pd
from datetime import datetime
import pytz
import os
import io, itertools
import csv
import warnings
import ntpath


def read_ysi_exo_csv(ysi_file,delim=None):
    """
    Method reads a text based YSI sonde instrument file in KOR EXO format and returns a pandas DataFrame for the table and metadata.

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

    #grab 30 lines discover what the real header is, then trim the file
    raw_metadata = pd.read_csv(ysi_file, sep=delim, engine='python',na_values=['','na'],header=None, nrows=30)
    header_row_index = raw_metadata.loc[raw_metadata[0].str.contains("Date")==True].index[0]
    raw_metadata = raw_metadata.drop(raw_metadata.index[(header_row_index-2):])

    #grab main file from header point, squash datetime row
    DF = pd.read_csv(ysi_file, parse_dates={'Datetime_(UTC)': [0,1,2]}, sep=delim, engine='python',na_values=['','na'], header = header_row_index)
    DF = DF.drop(DF.index[:header_row_index])


    metadata = pd.DataFrame(columns=('Manufacturer', 'Instrument_Serial_Number', 'Sensor_Serial_Numbers', 'Model','Station','Deployment_Setup_Time', \
                                     'Deployment_Start_Time', 'Deployment_Stop_Time','Filename','User','Averaging','Firmware', 'Sensor_Firmware'))
  
    metadata = metadata.append([{'Model' : 'EXO'}])
    metadata = metadata.set_value([0], 'Manufacturer' ,'YSI')
    metadata = metadata.set_value([0], 'Instrument_Serial_Number' ,raw_metadata.iloc[4][1].replace('Sonde ', ''))
    metadata = metadata.set_value([0], 'Station' ,raw_metadata.iloc[6][1])
    metadata = metadata.set_value([0], 'User' ,raw_metadata.iloc[5][1])
    metadata = metadata.set_value([0], 'Averaging' ,raw_metadata.iloc[8][1])
    metadata = metadata.set_value([0], 'Firmware' ,raw_metadata.iloc[16][2])
    head, tail = ntpath.split(ysi_file)
    metadata = metadata.set_value([0], 'Filename' , tail)
    metadata['Deployment_Start_Time'] = DF['Datetime_(UTC)'].iloc[0]
    metadata['Deployment_Stop_Time'] = DF['Datetime_(UTC)'].iloc[-1]
    sensors = raw_metadata.iloc[15:, 0:3]
    metadata = metadata.set_value([0], 'Sensor_Serial_Numbers' , sensors[1].str.cat(sep=';'))
    metadata = metadata.set_value([0], 'Sensor_Firmware' , sensors[2].str.cat(sep=';'))

    DF = DF.drop(['Site Name'], axis=1)
    for col in DF.columns:
        if 'Datetime_(UTC)' in col:
            continue
        param = col.split()
        submatch = DEFINITIONS[DEFINITIONS['parameter'].str.contains(param[0])]
        if submatch.empty:
            warnings.warn("Could not match parameter <%s> to definition file" %str(col) , stacklevel=2)
     
        if "Unnamed" not in col[1]:  #check for a null value in the units column
            match = submatch[submatch['unit'].str.contains(param[1])]
        else:
            DF = DF.rename(columns={col: str(submatch.iloc[0]['standard'])})
            
        if not match.empty:
                DF = DF.rename(columns={col: str(match.iloc[0]['standard'])})

    #now convert all data rows to floats...
    #move this to separate function if I have to do this more than for hydrotechs
    floater = lambda x: float(x)

    #split set
    dt_column = DF.iloc[:,0]
    data = DF.iloc[:,1:]
    data = data.applymap(floater)
    

    DF = pd.concat([dt_column,data], axis=1)

    
    return metadata, DF