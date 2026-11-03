'''
Module containing utility functions to be used with ROOT dataframes
'''
import re
import ROOT
import pandas  as pnd
import awkward as ak
import numpy

from dataclasses import dataclass
from functools   import lru_cache
from typing      import Union
from ROOT        import RDF, Numba
from dmu         import LogStore
from dmu.generic import hashing

log = LogStore.add_logger('dmu:rdataframe:utilities')
# ---------------------------------------------------------------------
@dataclass
class Data:
    '''
    Class meant to store data that is shared
    '''
    l_good_type = [int, numpy.bool_, numpy.int32, numpy.uint32, numpy.int64, numpy.uint64, numpy.float32, numpy.float64]
    d_cast_type = {'bool': numpy.int32}
# ---------------------------------------------------------------------
def columns_from_rdf(rdf : RDF.RNode) -> list[str]:
    '''
    Parameters
    --------------
    rdf: ROOT dataframe

    Returns
    --------------
    List of columns
    '''

    l_str = [ name.c_str() for name in rdf.GetColumnNames() ]

    return l_str
# ---------------------------------------------------------------------
def add_column(rdf : RDF.RNode, arr_val : Union[numpy.ndarray,None], name : str, d_opt : dict[str,str | None] | None = None):
    '''
    Will take a dataframe, an array of numbers and a string
    Will add the array as a colunm to the dataframe

    d_opt (dict) : Used to configure adding columns
         exclude_re : Regex with patter of column names that we won't pick
    '''

    log.warning(f'Adding column {name} with awkward')

    d_opt = {} if d_opt is None else d_opt
    if arr_val is None:
        raise ValueError('Array of values not introduced')

    if 'exclude_re' not in d_opt:
        d_opt['exclude_re'] = None

    v_col_org = rdf.GetColumnNames()
    l_col_org = [name.c_str() for name in v_col_org ]
    l_col     = []

    tmva_rgx  = r'tmva_\d+_\d+'

    for col in l_col_org:
        user_rgx = d_opt['exclude_re']
        if user_rgx is not None and re.match(user_rgx, col):
            log.debug(f'Dropping: {col}')
            continue

        if                          re.match(tmva_rgx, col):
            log.debug(f'Dropping: {col}')
            continue

        log.debug(f'Picking: {col}')
        l_col.append(col)

    data  = ak.from_rdataframe(rdf, columns=l_col) # type: ignore
    d_data= { col : data[col] for col in l_col }

    if arr_val.dtype == 'object':
        arr_val = arr_val.astype(float)

    d_data[name] = ak.from_numpy(arr_val) # type: ignore

    rdf = ak.to_rdataframe(d_data)

    return rdf
# ---------------------------------------------------------------------
def add_column_with_numba(
    rdf        : RDF.RNode,
    arr_val    : numpy.ndarray,
    name       : str,
    identifier : str) -> RDF.RNode:
    '''
    Will take a dataframe, an array of numbers and a string
    Will add the array as a colunm to the dataframe

    The `identifier` argument is a string need in order to avoid collisions
    when using Numba to define a function to get the value from.
    '''
    identifier=f'fun_{identifier}'

    @Numba.Declare(['int'], 'float', name=identifier)
    def get_value(index : int):
        return arr_val[index]

    log.debug(f'Adding column {name} with numba')
    rdf = rdf.Define(name, f'Numba::{identifier}(rdfentry_)')

    return rdf
# ---------------------------------------------------------------------
def rdf_report_to_df(rep : RDF.RCutFlowReport) -> pnd.DataFrame:
    '''
    Parameters
    ------------------
    rep: output of rdf.Report(), i.e. an RDataFrame cutflow report.

    Returns
    ------------------
    A pandas dataframe with the total, failed, efficiency, and cumulative efficiency
    If no cut was applied, raises ValueError
    '''
    if rep.begin() == rep.end():
        raise ValueError('Empty cutflow report')

    d_data = {'cut' : [], 'All' : [], 'Passed' : []}
    for cut in rep:
        name=cut.GetName()
        pas =cut.GetPass()
        tot =cut.GetAll()

        d_data['cut'   ].append(name)
        d_data['All'   ].append(tot)
        d_data['Passed'].append(pas)

    df = pnd.DataFrame(d_data)
    df['Efficiency' ] = df['Passed'] / df['All'].replace(0, pnd.NA)
    df['Cummulative'] = df['Efficiency'].cumprod()

    return df
# ---------------------------------------------------------------------
def random_filter(rdf : RDF.RNode, entries : int) -> RDF.RNode:
    '''
    Filters a dataframe, such that the output has **approximately** `entries` entries
    '''
    ntot = rdf.Count().GetValue()

    if entries <= 0 or entries >= ntot:
        log.warning(f'Requested {entries}/{ntot} random entries, not filtering')
        return rdf

    prob = float(entries) / ntot
    name = f'filter_{entries}'

    rdf  = rdf.Define(name, 'gRandom->Rndm();')
    rdf  = rdf.Filter(f'{name} < {prob}', name)
    nres = rdf.Count().GetValue()

    log.debug(f'Requested {ntot}, picked {nres}')

    return rdf
# ---------------------------------------------------------------------
def rdf_to_df(
    rdf     : RDF.RNode,
    columns : list[str]) -> pnd.DataFrame:
    '''
    Parameters
    ---------------
    rdf      : ROOT dataframe
    branches : List of columns to keep in pandas dataframe

    Returns
    ---------------
    Pandas dataframe with subset of columns
    '''
    log.debug('Storing branches')
    data     = rdf.AsNumpy(columns)
    df       = pnd.DataFrame(data)

    if len(df) == 0:
        rep      = rdf.Report()
        cutflow  = rdf_report_to_df(rep)
        log.warning('Empty dataset:\n')
        log.info(cutflow)

    return df
# ---------------------------------------------------------------------
def get_sample_definer_expression(samples : dict[str,int]) -> str:
    '''
    Parameters
    ---------------
    samples: Dictionary mapping file path to quantity associated

    Returns
    ---------------
    String where return value (year, block, etc) will be provided for given sample. This is used to define
    sample-wise columns as:

    ```python
    expr = get_sample_definer_expression(samples = samples)
    rdf  = rdf.DefinePerSample('year', expr)
    ```
    '''
    data = tuple(sorted(samples.items()))

    return _get_sample_definer_expression_cached(samples = data)
# ---------------------------------------------------------------------
@lru_cache()
def _get_sample_definer_expression_cached(samples : tuple[tuple[str,int],...]) -> str:
    if len(samples) == 0:
        raise ValueError('Found no entries for patching')

    hsh = hashing.hash_object(obj = [samples])

    inserts = ''
    for file_name, value in samples:
        inserts += f'tmp["{file_name}"] = {value};' + '\n'

    text = rf'''
    int GetValue_{hsh}(const std::string &name)
    {{
        static const std::map<std::string,int> entries_{hsh} = []{{
            std::map<std::string,int> tmp;
            {inserts}
            return tmp;
        }}();

        auto it = entries_{hsh}.find(name);
        return it == entries_{hsh}.end() ? -999 : it->second;
    }}
    '''

    ROOT.gInterpreter.Declare(text)

    return f'''
    auto name_{hsh}  = rdfsampleinfo_.AsString();

    return GetValue_{hsh}(name_{hsh});
    '''
# ---------------------------------------------------------------------
