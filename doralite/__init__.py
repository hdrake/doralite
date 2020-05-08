import cftime
import io
import json
import nc_time_axis
import os
import pandas as pd
import requests

api = 'https://dora-dev.gfdl.noaa.gov/cgi-bin/analysis/'

class DoraDataFrame(pd.DataFrame):
    def smooth(self,window,extrap=False):
        _df = self.rolling(window,center=True).mean()
        if extrap is True:
            _df.fillna(method='ffill',inplace=True)
            _df.fillna(method='bfill',inplace=True)
        return _df

def dora_metadata(expid):
    query = api+'meta.py?id='+str(expid)
    x = requests.get(url=query).content
    x = json.loads(x)
    x['pathHistory'] = x['pathPP'].replace('/pp','/history')
    return x
    

def search(string, attribute='pathPP'):
    """Returns dictionary of an attribute keyed by the id of experiments
    matching "string".

    By default, the returned attribute is the post-processing path ("pathPP")
    but others such as "pathDB", "pathAnalysis" and "expName" are allowed.
    If no match is found an empty dictionary is returned."""
    query = api+'search.py?search='+str(string)
    x = json.loads( requests.get(url=query).content )
    return dict((int(k),x[k][attribute]) for k in x.keys())

def global_mean_data(expid,component,varlist=None,start=None,end=None,yearshift=None,
        output='dataframe',showquery=False):
    '''
    Fetches global means from central server
    '''
    query_dict = {}
    query_dict['id'] = str(expid)
    query_dict['component'] = component
    if start is not None:
        query_dict['start'] = str(start)
    if end is not None:
        query_dict['end'] = str(end)
    if yearshift is not None:
        query_dict['yearshift'] = str(yearshift)

    query = []
    for q in iter(query_dict):
        query.append('='.join((q,query_dict[q])))

    query = '&'.join(query)
    query = api+'api.py?'+query

    if component == 'c4mip':
       query = api+'c4mip.py?id='+str(expid)

    if showquery:
        print(query)

    x = requests.get(url=query).content

    if output == 'csv':
        return io.StringIO(x.decode('utf8'))

    if output == 'dataframe':
        if component == 'c4mip':
            df = pd.read_csv(io.StringIO(x.decode('utf8')),comment='#',delim_whitespace=True)
            df.set_index('YEAR',inplace=True)
        else:
            df = pd.read_csv(io.StringIO(x.decode('utf8')),comment='#')
            df['year'] = cftime.num2date((df.year * 365.) - (365./2.) - 1,'days since 0001-01-01',calendar='365_day')
            #d_time = cftime.num2date((df.year * 365.) - (365./2.),'days since 0001-01-01',calendar='365_day')
            #df['year'] = [nc_time_axis.CalendarDateTime(item, "365_day") for item in d_time]
            df.rename(columns={'year':'date'},inplace=True)
            df.set_index('date',inplace=True)
            df = DoraDataFrame(df)
            _meta = dora_metadata(expid)
            df.id = _meta['id']
            df.title = _meta['expName']
        return df