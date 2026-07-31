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
    decay : str
    value : float
    error : float
    # ---------------------------------------
    def __mul__(self, other : 'BranchingFraction') -> 'BranchingFraction':
        val = self.value * other.value
        var = (self.value * other.error) ** 2 + (self.error * other.value) ** 2
        err = math.sqrt(var)

        decay = f'{self.decay} * {other.decay}'

        return BranchingFraction(decay = decay, value = val, error = err)
    # ---------------------------------------
    def __str__(self) -> str:
        return f'''
        Decay: {self.decay}
        Value: {self.value:.3g}
        Error: {self.error:.3g}
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
                tot_brf = cls(decay = decay, value = val, error = err)
            else:
                tot_brf = cls(decay = decay, value = val, error = err) * tot_brf

            log.debug(tot_brf)

        if tot_brf is None:
            raise ValueError(f'Cannot calculate branching fraction for decays: {decays}')

        tot_brf.decay = latex

        log.debug(tot_brf)

        return tot_brf
# ---------------------------------------
