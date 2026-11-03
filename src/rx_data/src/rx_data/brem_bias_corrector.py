'''
Module holding brem bias corrector class
'''
from typing                 import Union
from importlib.resources    import files

import yaml
import numpy
from vector                 import MomentumObject4D as v4d

from dmu.logging.log_store  import LogStore
from ecal_calibration       import calo_translator as ctran

log=LogStore.add_logger('rx_data:brem_bias_corrector')
# --------------------------
class BremBiasCorrector:
    '''
    Class meant to correct bias of brem energy
    '''
    # --------------------------
    def __init__(self):
        self._d_corr  = self._load_yaml(pattern='mu_data_24c4MU_bybin_P_ELECTRONENERGY_regionREGION.yaml')
        self._d_bound = self._load_yaml(pattern='regionREGION_bins.yaml')
    # --------------------------
    def _load_yaml(self, pattern : str) -> dict:
        path_pattern = files('ecal_calibration_data').joinpath(f'brem_correction/{pattern}')
        path_pattern = str(path_pattern)

        d_bound = {}
        for region in [0,1,2]:
            path = path_pattern.replace('REGION', str(region))
            with open(path, encoding='utf-8') as ifile:
                d_bound[region] = yaml.safe_load(ifile)

        return d_bound
    # --------------------------
    def _find_among_bounds(self, x : float, y : float, l_l_bound : list) -> Union[None, int]:
        for ibound, [xmin, xmax, ymin, ymax] in enumerate(l_l_bound):
            if (xmin < x < xmax) and (ymin < y < ymax):
                return ibound

        return None
    # --------------------------
    def _find_bin(self, x : float, y : float) -> Union[None, tuple]:
        for region, l_l_bound in self._d_bound.items():
            ibin = self._find_among_bounds(x, y, l_l_bound)
            if ibin is None:
                continue

            return ibin, region

        log.warning(f'Cannot find ({x:.3f}, {y:.3f}) among bounds')

        return None
    # --------------------------
    def _find_corrections(self, ibin : int, region : int) -> dict:
        d_corr_reg = self._d_corr[region]
        key        = region * 10_000 + ibin
        key        = str(key)

        correction = d_corr_reg[key]

        return correction
    # --------------------------
    def _apply_correction(self, brem : v4d, d_corr : dict) -> v4d:
        l_bound = d_corr['p']
        ibin    = numpy.digitize(brem.e, l_bound)
        index   = ibin - 1 if ibin > 0 else 0

        l_corr  = d_corr['mu']
        try:
            mu = l_corr[index]
        except IndexError:
            log.warning(f'Cannot find bin with correction for brem energy {brem.e:.0f} at index {index} among:')
            log.info(l_corr)
            log.info(l_bound)
            return brem

        if mu < 0.5 or mu > 3.0:
            log.warning(f'Found mu={mu:.3f} from:')
            log.info(l_corr)

        px      = brem.px / mu
        py      = brem.py / mu
        pz      = brem.pz / mu
        e_corr  = brem.e  / mu

        brem_corr = v4d(px=px, py=py, pz=pz, e=e_corr)

        return brem_corr
    # --------------------------
    def correct(
        self,
        brem : v4d,
        row  : int,
        col  : int,
        area : int) -> v4d:
        '''
        Takes 4 vector with brem, the row and column locations in ECAL
        Returns corrected photon
        '''
        x, y         = ctran.from_id_to_xy(row=row, col=col, area=area)
        val          = self._find_bin(x, y)
        if val is None:
            return brem

        ibin, region = val
        d_corr       = self._find_corrections(ibin, region)
        brem_corr    = self._apply_correction(brem, d_corr)

        return brem_corr
# --------------------------
