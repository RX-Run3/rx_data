'''
Module holding BrachingFraction class
'''
import math

from pydantic    import BaseModel
from dmu.generic import utilities as gut
from dmu         import LogStore

log=LogStore.add_logger('rx_common:branching_fraction')
# ---------------------------------------
class BranchingFraction(BaseModel):
    '''
    Class representing braching fractions
    '''
    dec : str
    val : float
    err : float
    # ---------------------------------------
    def __mul__(self, other : 'BranchingFraction') -> 'BranchingFraction':
        val = self.val * other.val
        var = (self.val * other.err) ** 2 + (self.err * other.val) ** 2
        err = math.sqrt(var)

        decay = f'{self.dec} * {other.dec}'

        return BranchingFraction(dec = decay, val = val, err = err)
    # ---------------------------------------
    def __str__(self) -> str:
        return f'''
        Decay: {self.dec}
        Value: {self.val:.3g}
        Error: {self.err:.3g}
        '''
    # ---------------------------------------
    @classmethod
    def from_decays(cls, decays : list[str], latex : str) -> 'BranchingFraction':
        '''
        Parameters
        ---------------
        decays: List of strings representing subdecays
        latex : Latex string representing full decay

        Returns
        ---------------
        Instance of decay branching fraction, errors propagated without correlation
        '''
        data = gut.load_data(
            fpath   = 'scales/fr_bf.yaml',
            package = 'rx_efficiencies_data')

        bfs : dict[str,list[float]] = data['bf']

        tot_brf : BranchingFraction | None = None
        for decay in decays:
            [val, err] = bfs[decay]
            if tot_brf is None:
                tot_brf = cls(dec = decay, val = val, err = err)
            else:
                tot_brf = cls(dec = decay, val = val, err = err) * tot_brf

            log.debug(tot_brf)

        if tot_brf is None:
            raise ValueError(f'Cannot calculate branching fraction for decays: {decays}')

        tot_brf.dec = latex

        log.debug(tot_brf)

        return tot_brf
# ---------------------------------------
