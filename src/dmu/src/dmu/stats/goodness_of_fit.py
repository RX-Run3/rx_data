'''
Module holding GoodnessOfFit class
'''
import math
import numpy

from pydantic    import BaseModel, model_validator
from scipy.stats import chi2 as chi2_dist
from typing      import Any, Final
from dmu         import LogStore

# Relative tolerance used to validate chi2
_CHI2_RTOL: Final[float] = 1e-3
# Relative tolerance used to validate pvalue
_PVAL_RTOL: Final[float] = 1e-7
# If pvalue is smaller than this, do not validate
_PVAL_MIN : Final[float] = 1e-7

_MIN_NDOF : Final[int  ] =  9
_MAX_NDOF : Final[int  ] = 41

log = LogStore.add_logger('rx_stats:fit_result')
# -----------------------------------------------
class GoodnessOfFit(BaseModel, frozen = True):
    '''
    Class meant to represent Chi2 or p-value from a fit
    '''
    chi2: float = math.nan
    pval: float = math.nan
    ndof: int
    # --------------------------
    @model_validator(mode='before')
    @classmethod
    def compute_or_validate(cls, data : Any):
        '''
        Validates:

        - NODF is between bounds
        - Chi2 or Pvalue needs to exist
        - If both chi2 and pvalue exist, check consistency
        '''
        chi2 : float = data.get('chi2', math.nan)
        pval : float = data.get('pval', math.nan)
        ndof : float = data['ndof']

        if not (_MIN_NDOF < ndof < _MAX_NDOF):
            raise ValueError(f'Invalid Ndof: {ndof}')

        if math.isnan(chi2) and math.isnan(pval):
            raise ValueError('Either pvalue or chi2 are needed')

        computed_pval = float(1 - chi2_dist.cdf(chi2, ndof))
        computed_chi2 = float(chi2_dist.isf(pval, ndof))
        # ----------------
        # Good input values
        # ----------------
        if not math.isnan(pval) and math.isclose(pval, 0.0, rel_tol = _PVAL_RTOL):
            log.debug(f'Input pvalue is zero: {pval:.3e}')
            data['chi2'] = 999
            return data
        # ----------------
        # Good computed values
        # ----------------
        if not math.isnan(computed_pval) and math.isclose(computed_pval, 0.0, rel_tol = _PVAL_RTOL):
            log.debug(f'Computed p-value is zero: {computed_pval:.3e}')

        if not math.isnan(computed_chi2) and math.isinf(computed_chi2):
            raise ValueError('Computed chi2 is inf')
        # ----------------
        # Got pvalue, not chi2, assign chi2
        # ----------------
        if   math.isnan(chi2) and not math.isnan(computed_chi2):
            data['chi2'] = computed_chi2
            return data
        elif math.isnan(chi2) and     math.isnan(computed_chi2):
            raise ValueError('Cannot compute chi2')
        # ----------------
        # Got chi2, not pvalue, assign pvalue
        # ----------------
        if   math.isnan(pval) and not math.isnan(computed_pval):
            data['pval'] = computed_pval
            return data
        elif math.isnan(pval) and     math.isnan(computed_pval):
            raise ValueError('Cannot compute pvalue')
        # ----------------
        # Pvalue too small to be validated, return
        # ----------------
        if          pval < _PVAL_MIN:
            return data

        if computed_pval < _PVAL_MIN:
            return data
        # ----------------
        # Got chi2 and pvalue, validate
        # ----------------
        if not math.isnan(chi2) and not numpy.isclose(chi2, computed_chi2, rtol = _CHI2_RTOL):
            raise ValueError(f'Inconsistent chi2 values: {chi2:.3} vs {computed_chi2:.3}')

        if not math.isnan(pval) and not numpy.isclose(pval, computed_pval, rtol = _PVAL_RTOL):
            raise ValueError(f'Inconsistent pvalue values: {pval:.7} vs {computed_pval:.7}')
        # ----------------

        return data
    # --------------------------
    def __str__(self) -> str:
        fchi2 = -1 if self.chi2 is None else self.chi2
        fpval = -1 if self.pval is None else self.pval
        indof = self.ndof

        msg = f'chi2: {fchi2:.0f}\n'
        msg+= f'pval: {fpval:.3f}\n'
        msg+= f'Ndof: {indof:}\n'

        return msg
    # --------------------------
    def __lt__(self, other : 'GoodnessOfFit') -> bool:
        '''
        Higher chi2 means worse goodness of fit
        '''
        return self.chi2 > other.chi2
# -----------------------------------------------
