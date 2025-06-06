'''
Module with ElectronBiasCorrector class
'''
import math
from typing                 import Union
from importlib.resources    import files

import pandas as pnd
from dmu.logging.log_store  import LogStore
from dmu.generic            import utilities        as gut
from vector                 import MomentumObject3D as v3d
from vector                 import MomentumObject4D as v4d

from ecal_calibration.preprocessor import PreProcessor
from ecal_calibration.corrector    import Corrector
from rx_data.brem_bias_corrector   import BremBiasCorrector

log=LogStore.add_logger('rx_data:electron_bias_corrector')
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
    def __init__(self, skip_correction : bool = False, brem_energy_threshold : float = 300):
        '''
        skip_correction: If true, will not correct electrons, but run all the code up to the last stage, default False
        brem_energy_threshold: Energy deposits in ECAL will be considered brem if their energy is above this value, default 300 MeV
        '''
        self._skip_correction = skip_correction
        self._mass            = 0.511
        self._min_brem_energy = brem_energy_threshold
        self._bcor            = BremBiasCorrector()
        self._name      : str
        self._corrector : Corrector

        # -1 : If the electron is not touched
        #  0 : If the electron is not assigned any brem
        #  1 : If the electron is assigned brem
        self._brem_status : int

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
        px = self._attr_from_row(row, f'{self._name}_{kind}PX')
        py = self._attr_from_row(row, f'{self._name}_{kind}PY')
        pz = self._attr_from_row(row, f'{self._name}_{kind}PZ')

        e_3d = v3d(px=px, py=py, pz=pz)
        pt   = e_3d.pt
        eta  = e_3d.eta
        phi  = e_3d.phi

        e_4d = v4d(pt=pt, eta=eta, phi=phi, mass=self._mass)
        e_4d = e_4d.to_pxpypzenergy()

        return e_4d
    # ---------------------------------
    def _get_ebrem(self, row : pnd.Series, e_track : v4d) -> v4d:
        e_full = self._get_electron(row, kind='')
        e_brem = e_full - e_track
        e_brem = e_brem.to_pxpypzenergy()

        self._check_massless_brem(e_brem)

        return e_brem
    # ---------------------------------
    def _check_massless_brem(self, e_brem : v4d) -> None:
        energy  = e_brem.e
        momentum= e_brem.p

        # Energy and momentum of brem photon need to be within 1 MeV.
        # Numerical issues might be making difference be in the 1e-3
        # 1 MeV is good enough
        if not math.isclose(energy, momentum, rel_tol=1):
            log.warning('Brem energy and momentum are not equal')
            log.info(f'{energy:.5f}=={momentum:.5f}')
        else:
            log.debug('Brem photon energy and momentum are close enough:')
            log.debug(f'{energy:.5f}=={momentum:.5f}')

        return e_brem
    # ---------------------------------
    def _update_row(self, row : pnd.Series, e_corr : v4d) -> pnd.Series:
        # If correction was not applied, do not update anything
        if e_corr is None:
            return row

        l_var = [
                f'{self._name}_PX',
                f'{self._name}_PY',
                f'{self._name}_PZ']

        row.loc[l_var] = [e_corr.px, e_corr.py, e_corr.pz]

        l_var = [
                f'{self._name}_PT' ,
                f'{self._name}_ETA',
                f'{self._name}_PHI']

        row.loc[l_var] = [e_corr.pt, e_corr.eta, e_corr.phi]

        row = self._update_brem(row)

        return row
    # ---------------------------------
    def _update_brem(self, row : pnd.Series) -> pnd.Series:
        if self._brem_status == -1:
            return row

        if self._brem_status not in [0, 1]:
            raise ValueError(f'Invalid brem status: {self._brem_status}')

        row.loc[[f'{self._name}_HASBREMADDED']] = [self._brem_status]

        return row
    # ---------------------------------
    def _attr_from_row(self, row : pnd.Series, name : str) -> float:
        if hasattr(row, name):
            return getattr(row, name)

        for col_name in row.index:
            log.info(col_name)

        raise ValueError(f'Cannot find attribute {name} among:')
    # ---------------------------------
    def _get_corrector(self) -> Corrector:
        if hasattr(self, '_corrector'):
            return self._corrector

        config_path = files('rx_data_data').joinpath('calibration/ecal.yaml')
        config_path = str(config_path)

        log.info(f'Loading config for calibration: {config_path}')
        cfg         = gut.load_json(config_path)

        self._corrector = Corrector(cfg=cfg)

        return self._corrector
    # ---------------------------------
    def _scale_electron(self, e_corr : v4d, row : pnd.Series, name : str) -> Union[v4d, None]:
        '''
        e_corr  : Electron with brem added that needs correction by scaling factor "mu"
        row     : Pandas series with information on event
        name    : Name of lepton, L1 or L2, needed to build features from right electron
        '''
        if not self._use_ecal_calibration:
            return e_corr

        row['L1_brem'] = row['L1_HASBREMADDED']
        row['L2_brem'] = row['L2_HASBREMADDED']

        sr = PreProcessor.build_features(
            row        = row,
            lep        = name,
            skip_target= True)

        cor    = self._get_corrector()
        e_cali = cor.run(e_corr, row=sr)

        return e_cali
    # ---------------------------------
    def _correct_with_bias_maps(self, e_track : v4d, e_brem : v4d, row : pnd.Series) -> v4d:
        '''
        Takes track electron, brem and row in dataframe representing entry in TTree
        Returns electron after correction
        '''
        if self._skip_correction:
            log.warning('Skipping electron correction')
            self._brem_status = -1
            return e_track + e_brem

        # Will only correct brem, no brem => no correction
        if not self._attr_from_row(row, f'{self._name}_HASBREMADDED'):
            self._brem_status = -1
            return e_track + e_brem

        log.info('Applying ecalo_bias correction')

        brem_row = self._attr_from_row(row, f'{self._name}_BREMHYPOROW')
        brem_col = self._attr_from_row(row, f'{self._name}_BREMHYPOCOL')
        brem_area= self._attr_from_row(row, f'{self._name}_BREMHYPOAREA')

        e_brem_corr = self._bcor.correct(brem=e_brem, row=brem_row, col=brem_col, area=brem_area)

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

        self._brem_status = 1
        e_corr = e_track + e_brem_corr

        return e_corr
    # ---------------------------------
    def _correct_with_track_brem_1(self, e_track : v4d, row : pnd.Series) -> v4d:
        '''
        Take electron from tracking system and brem, as well as dataframe row representing entry in TTree
        Create brem photon colinear to track, add it to track, return sum
        '''
        if self._skip_correction:
            self._brem_status = -1
            return None

        brem_energy = self._attr_from_row(row, f'{self._name}_BREMTRACKBASEDENERGY')
        if brem_energy < self._min_brem_energy:
            self._brem_status = 0
            return e_track

        eta = e_track.eta
        phi = e_track.phi

        gamma  = v4d(pt=1, eta=eta, phi=phi, m=0)
        factor = brem_energy / gamma.e

        px     = factor * gamma.px
        py     = factor * gamma.py
        pz     = factor * gamma.pz
        e      = factor * gamma.e

        gamma  = v4d(px=px, py=py, pz=pz, e=e)

        self._brem_status = 1
        self._check_massless_brem(gamma)

        return e_track + gamma
    # ---------------------------------
    def _correct_with_track_brem_2(self, e_track : v4d, row : pnd.Series, name : str) -> v4d:
        '''
        Smarter strategy than brem_track_1
        '''
        if self._attr_from_row(row, f'{self._name}_HASBREMADDED'):
            self._brem_status = -1
            log.info('Electron has already brem, skipping correction')
            e_corr = self._get_electron(row, kind='')
            e_corr = self._scale_electron(e_corr, row, name)
            return e_corr

        brem_energy = self._attr_from_row(row, f'{self._name}_BREMTRACKBASEDENERGY')
        if brem_energy <  self._min_brem_energy:
            log.info(f'Brem energy is below threshold: {brem_energy:.0f} < {self._min_brem_energy:.0f}')
            log.info('Skipping correction')
            self._brem_status = -1
            return None

        log.info('Correcting electron')
        e_corr = self._correct_with_track_brem_1(e_track, row)
        e_corr = self._scale_electron(e_corr, row, name)

        return e_corr
    # ---------------------------------
    def correct(self, row : pnd.Series, name : str, kind : str = 'brem_track_2') -> pnd.Series:
        '''
        Corrects kinematics and returns row
        row  : Pandas dataframe row
        name : Particle name, e.g. L1
        kind : Type of correction, [ecalo_bias, brem_track_1, brem_track_2]
        '''
        log.info(f'Correcting {name} with {kind}')

        self._name       = name
        self._brem_status= None

        e_track = self._get_electron(row, kind='TRACK_')

        if   kind == 'ecalo_bias':
            e_brem = self._get_ebrem(row, e_track)
            e_corr = self._correct_with_bias_maps(e_track, e_brem, row)
        elif kind == 'brem_track_1':
            e_corr = self._correct_with_track_brem_1(e_track, row)
        elif kind == 'brem_track_2':
            e_corr = self._correct_with_track_brem_2(e_track, row, name=name)
        else:
            raise NotImplementedError(f'Invalid correction of type: {kind}')

        if self._brem_status not in [-1, 0, 1]:
            raise ValueError(f'Brem status is invalid: {self._brem_status}')

        row = self._update_row(row, e_corr)

        return row
# ---------------------------------
