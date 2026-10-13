'''
Module holding ParsLoader class
'''

import os
import re
import numpy
import pandas as pnd

from typing   import Final
from pathlib  import Path
from dmu      import LogStore

log = LogStore.add_logger('rx_stats:pars_loader')

_NOMINAL  : Final[str] = 'nominal'
_NCOLUMNS : Final[int] = 2 # Number of columns

Npaint = numpy.ndarray[tuple[int], numpy.dtype[numpy.float64]]
# -------------------------------------------------
class ParsLoader:
    '''
    Class intended to:

    - Find parquet files with results from toy fits
    - Group/Merge corresponding datasets
    - Cleanup for failed fits, same toy has to have been fitted for different systematic variations
    - Offer data

    Requirements:

    - The nominal dataframes should be in files named as: nominal_003.parquet
    '''
    # ----------------------
    def __init__(
        self, 
        name : str):
        '''
        Parameters
        --------------
        name: Name of directory holding toys, e.g. v1
        '''
        self._name    = name
        self._regex   : Final[str] = r'(.*)_(\d{3})\.parquet'
        self._bts_rgx : Final[str] = r'bts_\d{3}_(.*)'    # bootstrapping regex
        self._del_rgx : Final[str] = r'delta_(.\d{2})_(.*)' # Normalization shift

        self._paths = self._get_paths()
        df          = self._paths_to_df(paths = self._paths)
        self._df    = self._check_df(df = df) 
    # ----------------------
    def _check_df(
        self, 
        df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df : Pandas dataframe with fitting parameters before validation 

        Returns
        -------------
        Dataframe after validation 
        '''
        hashes = df['Hash'].unique().tolist()
        seeds  = df['seed'].unique().tolist()

        nhash  = len(hashes)
        nseed  = len(seeds)

        if nhash != nseed:
            raise ValueError(f'Number of hashes and toys is different, {nhash} != {nseed}')

        return df
    # ----------------------
    def __str__(self) -> str:
        '''
        '''
        npaths = len(self._paths)
        systematics = self._df['syst'].unique().tolist()

        msg  =  40 * '-' + '\n'
        msg += f'{"Quantity":<20}{"Value"}\n'
        msg +=  40 * '-' + '\n'
        msg += f'{"Name":<20}{self._name}\n'
        msg += f'{"nPaths":<20}{npaths}\n'
        msg += f'{"Systematics":<20}{systematics}\n'
        msg +=  40 * '-' + '\n'

        return msg
    # ----------------------
    def _get_paths(self) -> list[Path]:
        '''
        Returns
        -------------
        List of paths to parquet files with parameters
        from fits to toys
        '''
        ana_dir = os.environ['ANADIR']
        toy_dir = Path(ana_dir) / f'toys/{self._name}'

        wildcard= '*.parquet'
        paths   = list(toy_dir.glob(pattern = wildcard))
        if not paths:
            raise ValueError(f'No paths found in: {toy_dir} for {wildcard}')

        log.info(f'Found {len(paths)} paths')

        return paths
    # ----------------------
    def _delta_columns(self, df : pnd.DataFrame) -> dict[str,tuple[str,str]]:
        '''
        Parameters
        -------------
        df: Dataframe with columns representing systematic variations on POI
        they include delta_{DELTA}_{MODEL} columns

        Returns
        -------------
        Dictionary mapping {MODEL} to tuple with down and up {DELTA}
        '''
        data : dict[str,list[str]] = dict()
        for name in df.columns:
            mtc = re.match(self._del_rgx, name)
            if not mtc:
                continue

            model = mtc.group(2)
            if model not in data:
                data[model] = [name]
            else:
                data[model].append(name)

        return { model : self._get_deltas(strings = strings) for model, strings in data.items() }
    # ----------------------
    def _get_deltas(self, strings : list[str]) -> tuple[str,str]:
        '''
        Parameters
        -------------
        strings: List of column names corresponding to a model's delta variations

        Returns
        -------------
        Tuple with lower and upper variation
        '''
        if len(strings) != _NCOLUMNS:
            raise ValueError(f'Expected two column names, found: {strings}')

        neg_var = None
        pos_var = None
        for string in strings:
            mtc = re.match(self._del_rgx, string)
            if not mtc:
                raise ValueError(f'Failed to match: {string}')

            delta = int(mtc.group(1))
            if delta < 0:
                neg_var = string
            else:
                pos_var = string

        if neg_var is None or pos_var is None:
            raise ValueError(f'Either variation could not be found: {neg_var}, {pos_var}')

        return neg_var, pos_var
    # ----------------------
    def _info_from_path(self, path : Path) -> tuple[str,int]:
        r'''
        Parameters
        -------------
        path: Path to parquet file of the form, ../dir/{systematic}_\d{3}.parquet

        Returns
        -------------
        String {systematic} as shown above
        '''
        mtch = re.match(self._regex, path.name)
        if not mtch:
            raise ValueError(f'Cannot find path information in: {path.name} with {self._regex}')

        syst  = mtch.group(1)
        rseed = mtch.group(2)

        return syst, int(rseed)
    # ----------------------
    def _paths_to_df(self, paths : list[Path]) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        paths: List of paths to parquet files with all toys 

        Returns
        -------------
        DataFrame such that:

        A unique column, 'seed', is assigned to each entry based on
         - Random seed used for toys
         - Index of toy within job

        The columns will be:

        Parameter, Value, Error, Gen, Toy, GOF, Valid, seed, syst
        '''

        dataframes : list[pnd.DataFrame] = []
        for path in sorted(paths):
            systematic, rseed = self._info_from_path(path)

            try:
                df   = pnd.read_parquet(path = path)
            except Exception:
                log.warning(f'Could not read {path}')
                continue

            toy : Npaint = df['Toy'].to_numpy()

            # Seed used to make toy data was
            # built from rseed and toy index
            x    = toy + rseed
            y    = x * (x + 1) / 2.
            seed = y + rseed
            seed = seed.astype(int)

            df['seed'] = seed
            df['syst'] = systematic

            dataframes.append(df)

        df_merged = pnd.concat(dataframes)

        # Invalid fits should have a Value and Error of Nan
        # This should prevent pollution plots with information
        # from invalid fits
        df_merged.loc[~df_merged['Valid'], 'Value'] = numpy.nan
        df_merged.loc[~df_merged['Valid'], 'Error'] = numpy.nan

        return df_merged
    # ----------------------
    def _boots_model(self, name : str) -> str | None:
        '''
        Parameters
        -------------
        name: Name correspondig to systematic, e.g. bts_{INDEX}_{MODEL}

        Returns
        -------------
        MODEL in the above pattern if the name corresponds to patter, or else None
        '''
        mtch = re.match(self._bts_rgx, name)
        if not mtch:
            return None

        return mtch.group(1)
    # ----------------------
    def _bootstrap_df(
        self, 
        df   : pnd.DataFrame,
        model: str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df   : Dataframe with columns representing systematic variations
        model: Model name, e.g. jpsi_ee

        Returns
        -------------
        Subset of dataframe, containing only bootstrapping variations on this model
        '''
        columns = list() 
        for name in df.columns:
            if self._boots_model(name = name) is None:
                continue

            if not name.endswith(model):
                continue

            columns.append(name)

        return df[columns]
    # ----------------------
    def _reduce_bootstrap(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df: DataFrame with each column been a systematic variation of the POI
            It includes nominal and bts_{INDEX}_{MODEL}

        Returns
        -------------
        Input dataframe where all the INDEX values have been merged to give
        bts_{MODEL} columns

        Logic
        -------------
        For any toy dataset, the KDE is obtained N times and N fits are made

        - The POI is measured in each of these N times and a standard deviation S is calculated.
        - S represents the uncertainty on POI, added to POI, it represents the average bias, B, expected on it
        - B is denoted as bts_{MODEL} and used to replace the original columns
        - B can be treated the same as the other columns now, for e.g. plotting purposes
        '''
        models = { self._boots_model(name = name) for name in df.columns.to_list() }
        
        data : list[pnd.Series] = []
        for model in models:
            if model is None:
                continue

            # For explanation, check docstring
            df_model = self._bootstrap_df(df = df, model = model)
            std_poi  = df_model.std(axis = 1)
            kde_poi  = df['nominal'] + std_poi
            kde_poi  = kde_poi.rename(f'bts_{model}')

            data.append(kde_poi)

        df_boots      = pnd.concat(data, axis=1)
        boots_columns = [ name for name in df.columns if name.startswith('bts_') ]
        df_strip  = df.drop(columns = boots_columns)
        df_merged = pnd.concat([df_strip, df_boots], axis = 1)

        return df_merged
    # ----------------------
    def _reduce_deltanorm(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df: Dataframe with each column for a value of the POI under certain
        systemaic variation

        Returns
        -------------
        Same dataframe with columns like delta_{DELTA}_{MODEL} merged
        into delta_{MODEL}

        Logic
        -------------
        The resulting column needs to represent the effect on the nominal
        resulting from the variation in the yield of the component, for this:

        - Find both variations and pick the one with the largest effect, for each toy
        - Add that variation to the nominal and build the delta column
        '''
        sr_nm = df['nominal']

        data : dict[str,pnd.Series] = dict()

        columns = self._delta_columns(df = df)
        for model, (name_dn, name_up) in columns.items():
            sr_up = df[name_up]
            sr_dn = df[name_dn]

            # Check docstring for logic
            delta_up = (sr_up - sr_nm).abs()
            delta_dn = (sr_dn - sr_nm).abs()
            sr_delta = delta_up.combine(delta_dn, max)

            data[f'delta_{model}'] = sr_delta + sr_nm

        all_deltas = []
        all_deltas+= [ val for _, val in columns.values() ]
        all_deltas+= [ val for val, _ in columns.values() ]

        df_strip   = df.drop(columns = all_deltas)
        df_delta   = pnd.DataFrame(data)
        df         = pnd.concat([df_strip, df_delta], axis=1)
        
        return df
    # ----------------------
    def df_by_poi(self, poi : str) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        poi: Name of parameter of interest

        Returns
        --------------
        Pandas dataframe with value of parameter of interest for
        nominal and all systematic variations. i.e. the columns are

        dt_sig_N, Nominal, Alt_1, Alt_2...
        '''
        df = self._df.query(f'Parameter == \"{poi}\"')
        df = df.set_index(keys = 'seed', drop=True)

        data : dict[str,pnd.Series] = dict()
        for syst, df_syst in df.groupby('syst'):
            syst = str(syst)
            if syst.startswith('fix_'):
                continue

            data[syst] = df_syst['Value']

        df = pnd.DataFrame(data)
        df = self._reduce_bootstrap(df = df)
        df = self._reduce_deltanorm(df = df)

        return df
    # ----------------------
    def df_by_sys(self, sys : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        sys: Name of systematic, e.g. nominal
    
        Returns
        -------------
        Dataframe corresponding to current systematic
        each row represents a parameter
        '''
        df        = self._df.query(f'syst == \"{sys}\"')
        df['Toy'] = df['seed']
        df        = df.drop(columns = ['syst', 'seed', 'Hash'])

        return df
    # ----------------------
    def df_by_fix(self, poi : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        poi: Name of parameter of interest, e.g. dt_sig_N

        Returns
        -------------
        Dataframe with POI information as well as name of parameter
        that was fixed for current toy and number of fixed parameters, i.e.

        Value, Error, Gen, Fixed, nFixed, Valid
        '''
        df_nom = self._df.query('syst == \"nominal\"')
        tot_nfloat = len(df_nom['Parameter'].unique().tolist())
        log.debug(f'Found {tot_nfloat} floating parameters in nominal model')

        l_df : list[pnd.DataFrame] = [] 
        for syst, df in self._df.groupby('syst'):
            syst       = str(syst)
            fixed      = syst.startswith('fix_')
            is_nominal = syst == _NOMINAL 

            if not fixed and not is_nominal:
                continue

            nfloat = len(df['Parameter'].unique().tolist())
            nfixed = tot_nfloat - nfloat

            df          = df.query(f'Parameter == \"{poi}\"')
            df['Fixed' ]= syst
            df['nFixed']= nfixed 

            l_df.append(df)

        df = pnd.concat(l_df, axis=0)
        df = df.reset_index(drop=True)
        df = df.drop(columns = ['Parameter', 'Toy', 'GOF', 'syst', 'seed', 'Hash'])

        return df
# -------------------------------------------------
