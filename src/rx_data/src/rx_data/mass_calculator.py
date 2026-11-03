'''
Module containing MassCalculator class
'''
import pandas as pnd

from typing      import cast
from ROOT        import RDF
from particle    import Particle         as part
from vector      import MomentumObject4D as v4d
from dmu         import LogStore
from dmu.generic import typing_utilities as tut

log=LogStore.add_logger('rx_data:mass_calculator')
# ---------------------------
class MassCalculator:
    '''
    Class in charge of creating dataframe with extra mass branches
    These are meant to be different from the Swap branches because
    the full candidate is meant to be rebuilt with different mass
    hypotheses for the tracks
    '''
    # ----------------------
    def __init__(
        self,
        rdf             : RDF.RNode,
        with_validation : bool = False) -> None:
        '''
        Parameters
        -------------
        rdf            : ROOT dataframe
        with_validation: If True, will add extra columns needed for tests, default False
        '''
        self._rdf             = rdf
        self._with_validation = with_validation
    # ----------------------
    def _get_columns(self, row) -> pnd.Series:
        '''
        Returns
        -------------
        Row of pandas dataframe with masses
        '''
        evt  = tut.numeric_from_series(row, 'EVENTNUMBER',   int)
        run  = tut.numeric_from_series(row, 'RUNNUMBER'  ,   int)
        data : dict[str,float|int]= {'EVENTNUMBER' : evt, 'RUNNUMBER' : run}

        data['B_Mass_hdpipi'] = self._get_hxy_mass(row=row, x=211, y=211)
        data['B_Mass_hdkk'  ] = self._get_hxy_mass(row=row, x=321, y=321)

        if not self._with_validation:
            return pnd.Series(data)

        data['B_M'         ] = tut.numeric_from_series(row, 'B_M', float)
        data['B_Mass_check'] = self._get_hxy_mass(row=row, x= 11, y= 11)

        sr = pnd.Series(data)

        return sr
    # ----------------------
    def _get_hxy_mass(
        self,
        row : pnd.Series,
        x   : int,
        y   : int) -> float:
        '''
        Parameters
        -------------
        row: Series with event information
        x/y: PDG ID to replace L1/L2 lepton with

        Returns
        -------------
        Value of mass when leptons get pion, hadron, etc mass hypothesis
        '''
        log.verbose('')
        log.verbose(f'Finding B mass for tracks: {x}/{y}')

        name_1 = self._column_name_from_pdgid(pid=x, preffix='L1')
        name_2 = self._column_name_from_pdgid(pid=y, preffix='L2')

        log.verbose(f'Will use particles: {name_1}/{name_2}')

        had_4d = self._get_hadronic_system_4d(row=row)
        par_1  = self._get_particle(row=row, name=name_1, pid=x)
        par_2  = self._get_particle(row=row, name=name_2, pid=y)

        candidate = had_4d + par_1 + par_2
        candidate = cast(v4d, candidate)

        return candidate.mass
    # ----------------------
    def _column_name_from_pdgid(
        self,
        pid     : int,
        preffix : str) -> str:
        '''
        Parameters
        -------------
        pid    : Particle PDG ID
        preffix: E.g. L1

        Returns
        -------------
        Name of column in original ROOT dataframe, e.g.:
        11 (electron) => {preffix}
        211(pion)     => {preffix}_TRACK
        '''
        # If one needs to build with Hee or Hmumu, the kinematic branches are L*_P*
        if pid in [11, 13]:
            return preffix

        # If one needs to build with Hhh, the kinematic branches are L*_TRACK_P*
        if pid in [211, 321]:
            return f'{preffix}_TRACK'

        raise ValueError(f'Invalid PID: {pid}')
    # ----------------------
    def _get_hadronic_system_4d(self, row : pnd.Series) -> v4d:
        '''
        Parameters
        -------------
        row: Pandas series with event information

        Returns
        -------------
        Four momentum vector of hadronic system
        '''
        b_4d  = self._get_particle(row=row, name= 'B', pid=   0) # mass from B_M
        l1_4d = self._get_particle(row=row, name='L1', pid=None) # mass from PDG ID, taken from L*_ID
        l2_4d = self._get_particle(row=row, name='L2', pid=None) # mass from PDG ID, taken from L*_ID

        res   = b_4d - l1_4d - l2_4d
        res   = cast(v4d, res)

        return res
    # ----------------------
    def _get_particle(
        self,
        row  : pnd.Series,
        name : str,
        pid  : int|None) -> v4d:
        '''
        Parameters
        -------------
        row  : Pandas series with event information
        name : Name of particle whose 4D vector to extract
        pid  : PDG ID used to extract particle mass:
               0   : Use value from {name}_M branch
               None: Use PDG mass from particle with ID {name}_ID
               else: If numeric and non-zero, get mass from PDG using this ID

        Returns
        -------------
        4D vector for particle
        '''
        pt   = tut.numeric_from_series(row, f'{name}_PT' , float)
        et   = tut.numeric_from_series(row, f'{name}_ETA', float)
        ph   = tut.numeric_from_series(row, f'{name}_PHI', float)
        mass = self._mass_from_pid(pid=pid, name=name, row=row)

        return v4d(pt=pt, eta=et, phi=ph, mass=mass)
    # ----------------------
    def _mass_from_pid(self, pid : int|None, name : str, row : pnd.Series) -> float:
        '''
        Parameters
        -------------
        row  : Pandas series with event information
        name : Name of particle whose 4D vector to extract
        pid  : PDG ID used to extract particle mass:
               0   : Use value from {name}_M branch
               None: Use PDG mass from particle with ID {name}_ID
               else: If numeric and non-zero, get mass from PDG using this ID

        Returns
        -------------
        Mass of particle
        '''
        # At this point we might have L1_TRACK
        name = name.replace('TRACK_', '')

        if pid == 0:
            return tut.numeric_from_series(row, f'{name}_M', float)

        if pid is None:
            pid = tut.numeric_from_series(row, f'{name}_ID', int)

        particle = part.from_pdgid(pid)
        mass     = particle.mass
        if mass is None:
            raise ValueError(f'Cannot find mass of particle with ID: {pid}')

        return mass
    # ----------------------
    def _is_valid_column(self, name : str) -> bool:
        '''
        Parameters
        -------------
        name: Name of column in ROOT dataframe

        Returns
        -------------
        True or False, depending on wether this column is needed
        '''
        if name in ['EVENTNUMBER', 'RUNNUMBER', 'B_M', 'B_PT', 'B_ETA', 'B_PHI']:
            return True

        if name in ['L1_TRACK_PT', 'L1_TRACK_ETA', 'L1_TRACK_PHI']:
            return True

        if name in ['L2_TRACK_PT', 'L2_TRACK_ETA', 'L2_TRACK_PHI']:
            return True

        if name in ['L1_PT', 'L1_ETA', 'L1_PHI']:
            return True

        if name in ['L2_PT', 'L2_ETA', 'L2_PHI']:
            return True

        # Need the original masses
        if name in ['B_ID', 'L1_ID', 'L2_ID']:
            return True

        return False
    # ----------------------
    def _get_dataframe(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        pandas dataframe with only necessary information
        '''
        log.debug('Getting pandas dataframe from ROOT dataframe')

        l_col = [ name.c_str() for name in self._rdf.GetColumnNames() ]
        l_col = [ name         for name in l_col if self._is_valid_column(name=name) ]

        data  = self._rdf.AsNumpy(l_col)
        df    = pnd.DataFrame(data)

        return df
    # ----------------------
    def get_rdf(self) -> RDF.RNode:
        '''
        Returns
        -------------
        ROOT dataframe with only the new mass columns
        EVENTNUMBER and RUNNUMBER
        '''
        log.debug('Retrieving dataframe')
        df  = self._get_dataframe()

        log.debug('Calculating masses')
        df  = df.apply(self._get_columns, axis=1)

        log.debug('Building ROOT dataframe with required information')
        data= { name : df[name].to_numpy() for name in df.columns }
        rdf = RDF.FromNumpy(data)

        log.debug('Returning ROOT dataframe')
        return rdf
# ---------------------------
