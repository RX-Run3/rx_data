'''
Module storing MassBiasCorrector class
'''

import numpy
import pandas as pnd
import vector

from typing                   import cast, Final
from vector._methods          import VectorProtocolSpatial
from vector                   import MomentumObject3D as v3d
from vector                   import MomentumObject4D as v4d
from dmu                      import LogStore
from dmu                      import LogLevels
from dmu.generic              import typing_utilities as tut
from rx_common                import Project, Trigger

from .electron_bias_corrector import ElectronBiasCorrector

# TODO: Remove cast calls once vector be cleaned up

log=LogStore.add_logger('rx_data:mass_bias_corrector')

_EMASS        : Final[float]     = 0.511
_KMASS        : Final[float]     = 493.6
_PIMASS       : Final[float]     = 137.57
_MUON_PID     : Final[int]       = 13
_ELECTRON_PID : Final[int]       = 11
_INDEX_COLUMNS: Final[list[str]] = ['EVENTNUMBER', 'RUNNUMBER']
# ------------------------------------------
class InvalidID(Exception):
    def __init__(self, message : str) -> None:
        super().__init__(message)
# ------------------------------------------
class MassBiasCorrector:
    '''
    Class meant to correct B mass without DTF constraint
    by correcting biases in electrons due to:

    - Issues with brem recovery: For this we use the `ElectronBiasCorrector` with `brem_track_2` correction
    '''
    # ------------------------------------------
    def __init__(
        self,
        df                    : pnd.DataFrame,
        is_mc                 : bool,
        trigger               : Trigger,
        photon_veto_version   : str,
        skip_correction       : bool  = False,
        nthreads              : int   = 1,
        brem_energy_threshold : float = 400,
        ecorr_kind            : str   = 'brem_track_2'):
        '''
        Parameters
        --------------
        df                   : Pandas dataframe
        trigger              : Hlt2 trigger name
        photon_veto_version  : Version of file used to veto photons, e.g. v1
        skip_correction      : Will do everything but not correction. Needed to check that only the correction is changing data.
        nthreads             : Number of processes to use
        brem_energy_threshold: Lowest energy that an ECAL cluster needs to have to be considered a photon, used as argument of ElectronBiasCorrector, default 0 (MeV)
        ecorr_kind           : Kind of correction to be added to electrons, [ecalo_bias, brem_track]
        '''
        self._df : Final[pnd.DataFrame] = df
        self._is_mc                     = is_mc
        self._trigger                   = trigger
        self._skip_correction           = skip_correction
        self._nproc                     = nthreads

        if self._skip_correction:
            log.warning('Skipping correction')

        self._ebc             = ElectronBiasCorrector(
            photon_veto_version   = photon_veto_version,
            brem_energy_threshold = brem_energy_threshold)
        self._ecorr_kind      = ecorr_kind

        log.info(f'Using project: {self._trigger.project}')

        self._silence_logger(name = 'rx_data:brem_bias_corrector')
        self._silence_logger(name = 'rx_data:electron_bias_corrector')
    # ------------------------------------------
    def _silence_logger(self, name) -> None:
        logger = LogStore.get_logger(name=name)
        if logger is None:
            raise ValueError(f'Cannot get logger: {name}')

        # If a logger has been put in debug level
        # then it is not meant to be silenced here
        if logger.getEffectiveLevel() == LogLevels.debug:
            return

        LogStore.set_level(name, 50)
    # ------------------------------------------
    def _correct_electron(
        self,
        name : str,
        row  : pnd.Series) -> pnd.Series:
        '''
        Parameters
        -------------------
        name: Name of particle, e.g. L1
        row : Row in pandas dataframe

        Returns
        -------------------
        Series representing corrected (uncorrected) electron (muon)
        '''
        lep_id = tut.numeric_from_series(row=row, name=f'{name}_ID', numeric=int)
        if abs(lep_id) == _MUON_PID:
            return row

        if abs(lep_id) != _ELECTRON_PID:
            raise InvalidID(f'Unexpected lepton ID: {lep_id}')

        if self._skip_correction:
            return row

        row     = self._ebc.correct(
            row = row,
            name= name,
            kind= self._ecorr_kind)

        return row
    # ----------------------
    def _build_4dvec(self, particle : str, row : pnd.Series, mass : float) -> v4d:
        '''
        Parameters
        -------------
        particle: Particle name, e.g. L1
        row     : Pandas series with event information
        mass    : Mass of particle

        Returns
        -------------
        Lorentz vector for particle
        '''
        pt = tut.numeric_from_series(row, f'{particle}_PT' , float)
        eta= tut.numeric_from_series(row, f'{particle}_ETA', float)
        phi= tut.numeric_from_series(row, f'{particle}_PHI', float)

        return vector.obj(pt=pt, phi=phi, eta=eta, mass=mass)
    # ------------------------------------------
    def _calculate_variables(self, row : pnd.Series) -> pnd.Series:
        '''
        Parameters
        ----------------
        row: Series representing event

        Returns
        ----------------
        Series with recalculated kinematics, after corrections
        '''
        l1 = self._build_4dvec(particle='L1', row=row, mass=_EMASS)
        l2 = self._build_4dvec(particle='L2', row=row, mass=_EMASS)

        if   self._trigger.project in [Project.rk, Project.rk_no_pid]:
            hd = self._build_4dvec(particle= 'H', row=row, mass=_KMASS)
        elif self._trigger.project in [Project.rkst, Project.rkst_no_pid]:
            h1 = self._build_4dvec(particle='H1', row=row, mass=_KMASS)
            h2 = self._build_4dvec(particle='H2', row=row, mass=_PIMASS)

            hd = h1 + h2
            hd = cast(v4d, hd)
        else:
            raise ValueError(f'Invalid project: {self._trigger.project}')

        jp = l1 + l2
        bp = jp + hd

        jp = cast(v4d, jp)
        bp = cast(v4d, bp)

        bmass = bp.mass
        jmass = jp.mass

        bmass = -1 if numpy.isnan(bmass) else float(bmass)
        jmass = -1 if numpy.isnan(jmass) else float(jmass)

        # TODO: Needs to recalculate:
        # PIDe
        # ProbNNe
        d_data = {
            'B_M'    : bmass,
            'Jpsi_M' : jmass,
            # --------------
            'B_PT'   : bp.pt,
            'Jpsi_PT': jp.pt,
            # --------------
            'L1_PX'  : row.L1_PX,
            'L1_PY'  : row.L1_PY,
            'L1_PZ'  : row.L1_PZ,
            'L1_PT'  : row.L1_PT,
            # --------------
            'L2_PX'  : row.L2_PX,
            'L2_PY'  : row.L2_PY,
            'L2_PZ'  : row.L2_PZ,
            'L2_PT'  : row.L2_PT,
            # --------------
            'L1_HASBREMADDED' : row.L1_HASBREMADDED,
            'L2_HASBREMADDED' : row.L2_HASBREMADDED,
            }

        d_data[   'B_DIRA_OWNPV'] = self._calculate_dira(momentum=bp.to_Vector3D(), row=row, particle=   'B')
        d_data['Jpsi_DIRA_OWNPV'] = row['Jpsi_DIRA_OWNPV']

        sr = pnd.Series(d_data)

        return sr
    # ------------------------------------------
    def _calculate_dira(
        self,
        row      : pnd.Series,
        momentum : VectorProtocolSpatial,
        particle : str) -> float:
        '''
        Recalculates dira with brem corrected momentum

        Parameters
        ----------------
        row      : Series associated to candidate information
        momentum : Brem corrected momentum
        particle : String with name of particle, e.g. B, Jpsi
        '''
        pv_x = row[f'{particle}_BPVX']
        pv_y = row[f'{particle}_BPVY']
        pv_z = row[f'{particle}_BPVZ']

        sv_x = row[f'{particle}_END_VX']
        sv_y = row[f'{particle}_END_VY']
        sv_z = row[f'{particle}_END_VZ']

        pv   = v3d(x=pv_x, y=pv_y, z=pv_z)
        sv   = v3d(x=sv_x, y=sv_y, z=sv_z)
        dr   = sv - pv
        dr   = cast(v3d, dr)

        cos_theta = dr.dot(momentum) / (dr.mag * momentum.mag)

        return cos_theta
    # ------------------------------------------
    def _calculate_correction(self, row : pnd.Series) -> pnd.Series:
        row_cor = row
        row_cor = self._correct_electron('L1', row_cor)
        row_cor = self._correct_electron('L2', row_cor)

        # NOTE: The variable calculation has to be done on the row AFTER the correction
        row_cor = self._calculate_variables(row_cor)

        return row_cor
    # ------------------------------------------
    def _get_corrected_df(self) -> pnd.DataFrame:
        '''
        Returns
        -------------
        Dataframe after correction
        '''
        if self._nproc == 1:
            log.info('Using single process to correct data')
            return self._df.apply(self._calculate_correction, axis=1)

        raise ValueError(f'Cannot run with more than one worker, using: {self._nproc}')
    # ------------------------------------------
    @property
    def photons_vetoed(self) -> int:
        '''
        Number of photons vetoes in correction
        '''
        return self._ebc.photons_vetoed
    # ------------------------------------------
    @property
    def all_photons(self) -> int:
        '''
        Number of photons that would have been used if there had not been any veto
        '''
        return self._ebc.all_photons
    # ------------------------------------------
    def get_df(self, suffix: str|None = None) -> pnd.DataFrame:
        '''
        Parameters
        ------------
        suffix : If passed (by default not), will add this as the suffix of the column names

        Returns
        ------------
        corrected pandas dataframe
        '''
        log.info('Applying bias correction')

        df_corr = self._get_corrected_df()

        if suffix is not None:
            df_corr = df_corr.add_suffix(f'_{suffix}')

        for variable in _INDEX_COLUMNS:
            df_corr[variable] = self._df[variable]

        df_corr = df_corr.fillna(-1) # For some candidates the B mass after correction becomes NaN

        in_size = len(df_corr)
        ot_size = len(self._df)
        if in_size != ot_size:
            raise ValueError(f'Sizes of input and output dataframes differ, {in_size} != {ot_size}')

        return df_corr
# ------------------------------------------
