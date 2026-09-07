'''
Module containing Q2SmearCalculator class
'''
import os
import math
import pandas as pnd

from typing                         import Final
from functools                      import lru_cache
from ROOT                           import RDF # type: ignore
from rx_common                      import Channel, info
from dmu.generic                    import typing_utilities as tut
from dmu.logging.log_store          import LogStore
from dmu.generic.version_management import get_last_version

log = LogStore.add_logger('rx_q2:q2smear_corrector')

_JPSI_PDG_MASS : Final[float]     = 3096.9
_EXTRA_COLUMNS : Final[list[str]] = ['EVENTNUMBER', 'RUNNUMBER']
_PARTICLES     : Final[list[str]] = ['B', 'Jpsi']
_COLUMNS       : Final[list[str]] = [
    'B_Mass'   , 'Jpsi_Mass', 
    'B_TRUEID' , 'Jpsi_TRUEID',
    'B_TRUEM'  , 'Jpsi_TRUEM',
    'nbrem'    , 'block']
# ------------------------------------
class Q2SmearCorrector:
    '''
    Class intended to operate only on simulated datasets from the electron or muon channel to:

    - Read mass scales and resolutions
    - Calculate smeared and scaled masses
    - Returns smeared mass for each unsmeared mass, block and brem 
    '''
    # ------------------------------------
    def __init__(
        self, 
        channel      : Channel,
        add_original : bool = False):
        '''
        No arguments needed, inputs will be passed to `get_mass`

        Parameters
        -------------------
        channel     : E.g. ee or mm, needed to pick up the JSON file with scales
        add_original: If true (default False), will add unsmeared masses
        '''
        log.debug(f'Using Jpsi PDG mass: {_JPSI_PDG_MASS:.2f}')


        if not add_original:
            _expected = ['Jpsi_Mass_smr', 'B_Mass_smr', 'q2_smr']
        else:
            _expected = ['Jpsi_Mass_smr', 'B_Mass_smr', 'q2_smr', 'B_Mass', 'Jpsi_Mass']

        self._expected : Final[list[str]] = _expected
        self._channel  = channel
        self._df       = self._get_scales()
    # ------------------------------------
    def _get_scales(self) -> pnd.DataFrame:
        ana_dir = os.environ['ANADIR']
        par_dir = get_last_version(f'{ana_dir}/q2/fits', version_only=False)
        par_path= f'{par_dir}/parameters_{self._channel}.json'

        log.info(f'Reading scales from: {par_path}')
        df      = pnd.read_json(par_path)

        return df
    # ------------------------------------
    @lru_cache(maxsize = 10)
    def _read_quantity(self, nbrem : int, block : int, kind : str) -> float:
        df = self._df.query(f'block == {block} and brem == {nbrem}')

        if len(df) != 2:
            log.info(df)
            raise ValueError(f'Expected data and MC entries for brem/block: {nbrem}/{block}')

        if kind == 'mu_mc':
            mu_mc = df.loc[ (df['sample'] == 'sim'), 'mu_val' ].iloc[0]
            return mu_mc

        if kind == 'reso':
            sg_dt = df.loc[ (df['sample'] == 'dat'), 'sg_val' ].iloc[0]
            sg_mc = df.loc[ (df['sample'] == 'sim'), 'sg_val' ].iloc[0]
            return sg_dt / sg_mc

        if kind == 'scale':
            mu_dt = df.loc[ (df['sample'] == 'dat'), 'mu_val' ].iloc[0]
            mu_mc = df.loc[ (df['sample'] == 'sim'), 'mu_val' ].iloc[0]

            return mu_dt - mu_mc

        raise NotImplementedError(f'Invalid quantity: {kind}')
    # ------------------------------------
    def _smear_mass(
        self,
        row      : pnd.Series,
        particle : str) -> float:
        '''
        Parameters:
        ---------------
        row : DataFrame row representing candiate 

        Returns:
        ---------------
        Smeared mass
        '''
        block = tut.numeric_from_series(row=row, name='block', numeric=int)
        nbrem = tut.numeric_from_series(row=row, name='nbrem', numeric=int)
        recom = tut.numeric_from_series(row=row, name=f'{particle}_Mass', numeric=float)
        truem = tut.numeric_from_series(row=row, name=f'{particle}_TRUEM'         , numeric=float)

        mu_mc = self._read_quantity(nbrem=nbrem, block=block, kind='mu_mc')
        reso  = self._read_quantity(nbrem=nbrem, block=block, kind= 'reso')
        scale = self._read_quantity(nbrem=nbrem, block=block, kind='scale')

        mass  = truem + reso * (recom - truem) + scale + (1 - reso) * (mu_mc - _JPSI_PDG_MASS)

        log.verbose('')
        log.verbose(f'{truem=:.0f}, {recom=:.0f}, {reso=:.3f}, {scale=:.3f}, {mu_mc=:.0f}, {_JPSI_PDG_MASS=:.0f}')
        log.verbose(f'{(reso * (recom - truem))=:.0f}, {((1 - reso) * (mu_mc - _JPSI_PDG_MASS))=:.0f}')
        log.verbose(f'{recom:<20.0f}{"->":<20}{mass:<20.0f}')

        if not math.isnan(mass):
            return mass

        log.debug('')
        log.debug(f'{truem=:.0f}, {recom=:.0f}, {reso=:.3f}, {scale=:.3f}, {mu_mc=:.0f}, {_JPSI_PDG_MASS=:.0f}')
        log.debug(f'{(reso * (recom - truem))=:.0f}, {((1 - reso) * (mu_mc - _JPSI_PDG_MASS))=:.0f}')
        log.debug(f'{recom:<20.0f}{"->":<20}{mass:<20.0f}')

        return recom 
    # ----------------------
    def _process_data(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe with data

        Returns
        -------------
        ROOT dataframe with smeared variables, smearing is skipped
        '''
        columns = [f'{particle}_Mass' for particle in _PARTICLES ]
        log.info(f'Using {columns} columns for unsmeared dataset')

        data    = rdf.AsNumpy(columns)

        expanded= {}
        for name, array in data.items():
            new_name           = name.replace('_Mass', '_Mass_smr')
            expanded[new_name] = array
            expanded[    name] = array

        df = pnd.DataFrame(expanded)
        df = self._add_extra_columns(df=df, rdf=rdf)
        df = self._trim_columns(df=df)

        return RDF.FromPandas(df)
    # ----------------------
    def _add_extra_columns(
        self, 
        rdf : RDF.RNode,
        df  : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe with input data to be smeared
        df : DataFrame with smeared data

        Returns
        -------------
        Dataframe with extra columns, e.g. q2_smr
        '''
        df['q2_smr'] = df['Jpsi_Mass_smr'] * df['Jpsi_Mass_smr']

        data = rdf.AsNumpy(_EXTRA_COLUMNS)
        for name, values in data.items():
            df[name] = values

        return df
    # ----------------------
    def _trim_columns(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        df: Pandas dataframe with potentially not needed columns

        Returns
        -------------
        Dataframe with only the needed columns
        '''
        all_needed : Final[list[str]] = self._expected + _EXTRA_COLUMNS 

        columns = df.columns
        for column in columns:
            if column in all_needed:
                continue

            log.debug(f'Trimming: {column}')
            df = df.drop(columns=[column])

        return df
    # ----------------------
    def get_rdf(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe with mass columns to be smeared

        Returns
        -------------
        ROOT dataframe with data to be smeared 
        '''
        if info.is_rdf_data(rdf=rdf):
            log.info('DataFrame from real data, will return unsmeared variables')
            return self._process_data(rdf=rdf)

        data    = rdf.AsNumpy(_COLUMNS)
        df      = pnd.DataFrame(data)

        log.info('Smearing masses')
        for particle in _PARTICLES:
            log.debug(particle)
            df[f'{particle}_Mass_smr'] = df.apply(self._smear_mass, args=(particle,), axis=1)

        df = self._add_extra_columns(df=df, rdf=rdf)
        df = self._trim_columns(df=df)

        return RDF.FromPandas(df) 
# ------------------------------------
