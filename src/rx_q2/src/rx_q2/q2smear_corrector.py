'''
Module containing Q2SmearCalculator class
'''
import pandas as pnd

from typing      import Final
from ROOT        import RDF
from rx_common   import Block, Brem, Channel, Correction
from dmu         import LogStore

from .scale_reader import ScaleReader

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
    def __get_lookup(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        df: Pandas dataframe with entries representing candidates

        Returns
        --------------
        Dataframe with lookup table to associate input dataframe with scales
        '''
        combos  = df[['block', 'nbrem']].drop_duplicates()
        records = []

        # NOTE: Brem zero will be dropped anyway
        log.warning('Using fake scales for brem zero in electron channel')
        for _, row in combos.iterrows():
            block = Block(value=int(row['block']))
            brem  = Brem.from_int(int(row['nbrem']))

            if self._channel == Channel.ee and brem == Brem.zero:
                log.warning('Using dummy scales for brem zero')
                reso     = 1.0
                scale    = 0.0
                mu_mc    = 5280
            else:
                mu_mc, _ = self._reader.get_param(
                    is_mc= True,
                    param= 'mu',
                    block= block,
                    brem = brem)

                reso , _ = self._reader.get_scale(
                    corr = Correction.mass_resolution,
                    block= block,
                    brem = brem)

                scale, _ = self._reader.get_scale(
                    corr = Correction.mass_scale,
                    block= block,
                    brem = brem)

            data = {
                'block': row['block'],
                'nbrem': row['nbrem'],
                'mu_mc': mu_mc,
                'reso' : reso,
                'scale': scale}

            records.append(data)

        df = pnd.DataFrame(records)

        log.debug(20 * '-')
        log.debug('Scales:')
        log.debug(20 * '-')
        log.debug(f'\n{str(df)}')

        return df
    # ----------------------
    def _mass_from_particle(self, particle : str, df : pnd.DataFrame) -> pnd.Series:
        '''
        Parameters
        ------------------
        particle: Particle identity, i.e. Jpsi, B

        Returns
        ------------------
        Series with smeared arrays for given particle
        '''
        recom = df[f'{particle}_Mass']
        truem = df[f'{particle}_TRUEM']

        masses= (
                truem
                + df['reso'] * (recom - truem)
                + df['scale']
                + (1 - df['reso']) * (df['mu_mc'] - _BPLUS_PDG_MASS))

        return masses
    # ----------------------
    def _is_rdf_data(self, rdf : RDF.RNode) -> bool:
        '''
        Parameters
        -------------
        rdf: ROOT dataframe

        Returns
        -------------
        True for real data and false for MC
        '''
        log.debug('Checking for data')

        names = [ name.c_str() for name in rdf.GetColumnNames() ]
        trueid= [ name         for name in names if name.endswith('TRUEID')]

        return not trueid
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
        if self._is_rdf_data(rdf=rdf):
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
        lookup = self.__get_lookup(df = df)
        df     = df.merge(lookup, on=['block', 'nbrem'], how='left')

        log.info('Smearing masses')
        for particle in _PARTICLES:
            log.debug(particle)
            if replace:
                df[f'{particle}_Mass_org'] = df[f'{particle}_Mass'].to_numpy()
                df[f'{particle}_Mass'    ] = self._mass_from_particle(particle, df)
            else:
                df[f'{particle}_Mass_smr'] = self._mass_from_particle(particle, df)

        df = df.drop(columns=['mu_mc', 'reso', 'scale'])

        return df
# ------------------------------------
