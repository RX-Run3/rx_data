'''
Module containing Q2SmearCalculator class
'''
import math
import pandas as pnd

from fitter      import ScaleReader
from typing      import Final
from ROOT        import RDF # type: ignore
from rx_common   import Block, Brem, Channel, Correction, info
from dmu.generic import typing_utilities as tut
from dmu         import LogStore

log = LogStore.add_logger('rx_q2:q2smear_corrector')

_BPLUS_PDG_MASS: Final[float]     = 5279.41
_EXTRA_COLUMNS : Final[list[str]] = ['EVENTNUMBER', 'RUNNUMBER']
_PARTICLES     : Final[list[str]] = ['B', 'Jpsi']
_COLUMNS       : Final[list[str]] = [  # These are the expected columns in the 
    'B_Mass'   , 'Jpsi_Mass',          # input ROOT dataframe 
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
        log.debug(f'Using B+ PDG mass: {_BPLUS_PDG_MASS:.2f}')

        if not add_original:
            _expected = ['Jpsi_Mass_smr', 'B_Mass_smr', 'q2_smr']
        else:
            _expected = ['Jpsi_Mass_smr', 'B_Mass_smr', 'q2_smr', 'B_Mass', 'Jpsi_Mass']

        self._expected : Final[list[str]] = _expected
        self._channel  = channel
        self._reader   = ScaleReader(channel = channel)
    # ------------------------------------
    def _smear_from_row(
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
        block = tut.numeric_from_series(row=row, name='block'            , numeric=int)
        nbrem = tut.numeric_from_series(row=row, name='nbrem'            , numeric=int)
        recom = tut.numeric_from_series(row=row, name=f'{particle}_Mass' , numeric=float)
        truem = tut.numeric_from_series(row=row, name=f'{particle}_TRUEM', numeric=float)

        return self.__smear_mass(
            recom = recom, 
            truem = truem, 
            nbrem = Brem.from_int(nbrem), 
            block = Block(value = block))
    # ----------------------
    def __smear_mass(
        self, 
        recom : float, 
        truem : float, 
        nbrem : Brem, 
        block : Block) -> float:
        mu_mc, _ = self._reader.get_param(is_mc = True, param = 'mu', block = block, brem = nbrem)
        reso , _ = self._reader.get_scale(corr  = Correction.mass_resolution, block = block, brem = nbrem)
        scale, _ = self._reader.get_scale(corr  = Correction.mass_scale     , block = block, brem = nbrem)

        mass  = truem + reso * (recom - truem) + scale + (1 - reso) * (mu_mc - _BPLUS_PDG_MASS)

        log.verbose('')
        log.verbose(f'{truem=:.0f}, {recom=:.0f}, {reso=:.3f}, {scale=:.3f}, {mu_mc=:.0f}, {_BPLUS_PDG_MASS=:.0f}')
        log.verbose(f'{(reso * (recom - truem))=:.0f}, {((1 - reso) * (mu_mc - _BPLUS_PDG_MASS))=:.0f}')
        log.verbose(f'{recom:<20.0f}{"->":<20}{mass:<20.0f}')

        if not math.isnan(mass):
            return mass

        log.debug('')
        log.debug(f'{truem=:.0f}, {recom=:.0f}, {reso=:.3f}, {scale=:.3f}, {mu_mc=:.0f}, {_BPLUS_PDG_MASS=:.0f}')
        log.debug(f'{(reso * (recom - truem))=:.0f}, {((1 - reso) * (mu_mc - _BPLUS_PDG_MASS))=:.0f}')
        log.debug(f'{recom:<20.0f}{"->":<20}{mass:<20.0f}')

        return mass
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

        data = rdf.AsNumpy(_COLUMNS)
        df   = pnd.DataFrame(data)
        df   = self.get_df(df = df)
        df   = self._add_extra_columns(df=df, rdf=rdf)
        df   = self._trim_columns(df=df)

        return RDF.FromPandas(df) 
    # ----------------------
    def get_df(self, df : pnd.DataFrame, replace : bool = False) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        df     : Pandas dataframe with event per row
        replace: 
            True : will override mass columns, and keep original with `_org` suffix
            Talse: (default) will add new ones with `_smr` suffix
        '''
        log.info('Smearing masses')
        for particle in _PARTICLES:
            log.debug(particle)
            if replace:
                df[f'{particle}_Mass_org'] = df[f'{particle}_Mass'].to_numpy()
                df[f'{particle}_Mass'    ] = df.apply(self._smear_from_row, args=(particle,), axis=1)
            else:
                df[f'{particle}_Mass_smr'] = df.apply(self._smear_from_row, args=(particle,), axis=1)

        return df
# ------------------------------------
