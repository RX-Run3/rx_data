'''
Module with ElectronBiasCorrector class
'''
import math
import vector
import pandas as pnd

from typing               import Final, cast
from vector               import MomentumObject4D as v4d
from dmu                  import LogStore

from .brem_bias_corrector import BremBiasCorrector
from .photon_veto         import PhotonVeto

log=LogStore.add_logger('rx_data:electron_bias_corrector')
_ELECTRON_MASS : Final[float]=0.511
# ---------------------------------
class ElectronBiasCorrector:
    r'''
    Class meant to correct electron kinematics
    The correction is done by using the `kind` argument in the correct method. Supported arguments are:

    ecalo_bias: Will use the $\mu=E_{calo}/E_{track}$ to correct the brem energy of every electron. This will leave Brem 0 unchanged.
    brem_track_1: This will create a new Brem photon, colinear to the electron track with an energy given by `BREMTRACKBASEDENERGY`.
    brem_track_2: This will:
        - For electrons with brem: Do nothing
        - For electrons without brem: If `BREMTRACKBASEDENERGY > 50 MeV` add brem, otherwise do nothing.
        - Optionally, rescale energy of electron based on measurement of "mu" through the momentum closure.
    '''
    # ---------------------------------
    def __init__(
        self,
        photon_veto_version   : str,
        skip_correction       : bool  = False,
        brem_energy_threshold : float = 300):
        '''
        Parameters
        ---------------------------
        photon_veto_version  : Version of file with list of cells to veto when adding photon, e.g. v1
        skip_correction      : If true, will not correct electrons, but run all the code up to the last stage, default False
        brem_energy_threshold: Energy deposits in ECAL will be considered brem if their energy is above this value, default 300 MeV
        '''
        self._lep_name : str | None= None
        self._skip_correction      = skip_correction
        self._min_brem_energy      = brem_energy_threshold
        self._bcor                 = BremBiasCorrector()
        self._veto                 = PhotonVeto(version = photon_veto_version)

        # This will turn ON/OFF the code that reads the regressor
        # to apply the energy scaling to electrons based on kinematic balance
        self._use_ecal_calibration = True

        if self._skip_correction:
            log.warning('Skipping electron correction')
    # ---------------------------------
    def _get_electron(self, row : pnd.Series, kind : str) -> v4d:
        '''
        Parameters:

        kind : TRACK or empty string for track electron or full electron, respectively
        '''
        px = self._attr_from_row(row, f'{self._lep_name}_{kind}PX')
        py = self._attr_from_row(row, f'{self._lep_name}_{kind}PY')
        pz = self._attr_from_row(row, f'{self._lep_name}_{kind}PZ')

        e_3d = vector.obj(px=px, py=py, pz=pz)
        pt   = e_3d.pt
        eta  = e_3d.eta
        phi  = e_3d.phi

        e_4d = vector.obj(pt=pt, eta=eta, phi=phi, mass=_ELECTRON_MASS)
        e_4d = e_4d.to_pxpypzenergy()
        e_4d = cast(v4d, e_4d)

        return e_4d
    # ---------------------------------
    def _get_ebrem(self, row : pnd.Series, e_track : v4d) -> v4d:
        e_full = self._get_electron(row, kind='')
        e_brem = e_full - e_track
        e_brem = e_brem.to_pxpypzenergy()
        e_brem = cast(v4d, e_brem)

        self._check_massless_brem(e_brem)

        return e_brem
    # ---------------------------------
    def _check_massless_brem(self, e_brem : v4d) -> None:
        '''
        Checks if v4d representing brem is massless
        Parameters
        -------------
        e_brem: 4D vector representing brem

        Returns
        -------------
        Nothing, this just checks
        '''
        energy  = e_brem.e
        momentum= e_brem.p

        # Energy and momentum of brem photon need to be within 1 MeV.
        # Numerical issues might be making difference be in the 1e-3
        # 1 MeV is good enough
        if not math.isclose(energy, momentum, abs_tol=1):
            log.error(f'{energy:.1f}!={momentum:.1f}')
            raise ValueError('Brem energy and momentum are not equal')

        log.debug('Brem photon energy and momentum are close enough:')
        log.debug(f'{energy:.5f}=={momentum:.5f}')
    # ---------------------------------
    def _update_row(self, row : pnd.Series, e_corr : v4d|None) -> pnd.Series:
        '''
        Parameters
        ---------------
        row    : Pandas series with candidate information
        e_corr : None, if no correction needed, 4D vector if row needs update

        Returns
        ---------------
        Pandas series with updated candidate information, based on corrected electron
        '''
        if e_corr is None:
            log.debug('Electron was not brem corrected')
            return row

        log.debug('Electron was brem corrected')
        l_var = [
                f'{self._lep_name}_PX',
                f'{self._lep_name}_PY',
                f'{self._lep_name}_PZ']

        row.loc[l_var] = [e_corr.px, e_corr.py, e_corr.pz]

        l_var = [
                f'{self._lep_name}_PT' ,
                f'{self._lep_name}_ETA',
                f'{self._lep_name}_PHI']

        row.loc[l_var] = [e_corr.pt, e_corr.eta, e_corr.phi]
        row.loc[[f'{self._lep_name}_HASBREMADDED']] = [1]

        return row
    # ---------------------------------
    def _attr_from_row(self, row : pnd.Series, name : str) -> float:
        if hasattr(row, name):
            return getattr(row, name)

        for col_name in row.index:
            log.info(col_name)

        raise ValueError(f'Cannot find attribute {name} among:')
    # ---------------------------------
    def _correct_with_bias_maps(self, e_track : v4d, e_brem : v4d, row : pnd.Series) -> v4d:
        '''
        Takes track electron, brem and row in dataframe representing entry in TTree
        Returns electron after correction
        '''
        if self._skip_correction:
            log.warning('Skipping electron correction')
            e_corr = e_track + e_brem
            e_corr = cast(v4d, e_corr)

            return e_corr

        # Will only correct brem, no brem => no correction
        if not self._attr_from_row(row, f'{self._lep_name}_HASBREMADDED'):
            e_corr = e_track + e_brem
            e_corr = cast(v4d, e_corr)

            return e_corr

        log.info('Applying ecalo_bias correction')

        brem_row = self._attr_from_row(row, f'{self._lep_name}_BREMHYPOROW')
        brem_col = self._attr_from_row(row, f'{self._lep_name}_BREMHYPOCOL')
        brem_area= self._attr_from_row(row, f'{self._lep_name}_BREMHYPOAREA')

        e_brem_corr = self._bcor.correct(brem=e_brem, row=int(brem_row), col=int(brem_col), area=int(brem_area))

        if e_brem_corr.isclose(e_brem, rtol=1e-5):
            momentum = e_brem.p
            log.warning(f'Correction did not change photon at row/column/region/momentum: {brem_row}/{brem_col}/{brem_area}/{momentum:.0f}')
            log.info(e_brem)
            log.info('--->')
            log.info(e_brem_corr)
        else:
            log.debug('Brem was corrected:')
            log.debug(e_brem)
            log.debug('--->')
            log.debug(e_brem_corr)

        self._check_massless_brem(e_brem_corr)

        e_corr = e_track + e_brem_corr
        e_corr = cast(v4d, e_corr)

        return e_corr
    # ---------------------------------
    def _correct_with_track_brem_1(
        self,
        e_track : v4d,
        row     : pnd.Series) -> v4d | None:
        '''
        Parameters
        -------------
        e_track : 4-vector representing track associated to electron
        row     : Series holding candidate information

        Returns
        -------------
        4-vector with kinematics of brem photon and electron
        or None if no correction is needed on original electron
        '''
        if self._skip_correction:
            return None

        brem_energy = self._attr_from_row(row, f'{self._lep_name}_BREMTRACKBASEDENERGY')
        if brem_energy < self._min_brem_energy:
            return None

        eta = e_track.eta
        phi = e_track.phi

        gamma  = vector.obj(pt=1.0, eta=eta, phi=phi, mass=0.0)
        factor = brem_energy / gamma.e

        px     = factor * gamma.px
        py     = factor * gamma.py
        pz     = factor * gamma.pz
        e      = factor * gamma.e

        gamma  = vector.obj(px=px, py=py, pz=pz, e=e)

        self._check_massless_brem(gamma)

        e_corr = e_track + gamma
        e_corr = cast(v4d, e_corr)

        return e_corr
    # ---------------------------------
    def _correct_with_track_brem_2(
        self,
        e_track : v4d,
        row     : pnd.Series) -> v4d | None:
        '''
        Smarter strategy than brem_track_1

        Parameters
        ----------------
        e_track: 4-vector associated to electron's track
        row    : Pandas series with entry information

        Returns
        ----------------
        - 4-vector representing electron with brem added
        - None, if no brem needs/can be added
        '''
        if self._attr_from_row(row, f'{self._lep_name}_HASBREMADDED'):
            log.debug('Electron has already brem, skipping correction')
            return None

        brem_energy = self._attr_from_row(row, f'{self._lep_name}_BREMTRACKBASEDENERGY')
        if brem_energy <  self._min_brem_energy:
            log.debug(f'Brem energy is below threshold: {brem_energy:.0f} < {self._min_brem_energy:.0f}')
            log.debug('Skipping correction')
            return None

        log.debug('Correcting electron')
        e_corr = self._correct_with_track_brem_1(e_track, row)

        return e_corr
    # ---------------------------------
    @property
    def photons_vetoed(self) -> int:
        '''
        Number of photons vetoed when correcting electron brem
        '''
        return self._veto.nvetoed
    # ---------------------------------
    @property
    def all_photons(self) -> int:
        '''
        Number of photons that could have been added
        '''
        return self._veto.ntotal
    # ---------------------------------
    def correct(
        self,
        row  : pnd.Series,
        name : str,
        kind : str = 'brem_track_2') -> pnd.Series:
        '''
        Corrects kinematics and returns row

        Parameters
        --------------
        row  : Pandas dataframe row
        name : Particle name, e.g. L1
        kind : Type of correction, [ecalo_bias, brem_track_1, brem_track_2]
        '''
        log.debug(f'Correcting {name} with {kind}')

        self._lep_name = name
        e_track    = self._get_electron(row, kind='TRACK_')

        if self._veto.veto(row = row, lepton_name = self._lep_name):
            log.debug('Photon falls in vetoed ECAL region, skipping correction')
            row = self._update_row(row = row, e_corr = e_track)

            return row

        if   kind == 'ecalo_bias':
            e_brem = self._get_ebrem(row = row, e_track = e_track)
            e_corr = self._correct_with_bias_maps(e_track, e_brem, row)
        elif kind == 'brem_track_1':
            e_corr = self._correct_with_track_brem_1(e_track = e_track, row = row)
        elif kind == 'brem_track_2':
            e_corr = self._correct_with_track_brem_2(e_track = e_track, row = row)
        else:
            raise NotImplementedError(f'Invalid correction of type: {kind}')

        row = self._update_row(row = row, e_corr = e_corr)

        return row
# ---------------------------------
