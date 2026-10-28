'''
Module holding MCVarsAdder class
'''
import re

from ROOT      import RDF
from typing    import Final
from functools import cached_property
from dmu       import LogStore

log = LogStore.add_logger('post_ap:mc_vars_adder')

MC_REGEX : Final[str] = r'mc_\d{2}_(w\d{2}_\d{2}|w\d{2})_mag(up|down)_sim\d+\w_(\d{8})_.*'
# -----------------------------
class MCVarsAdder:
    '''
    Class intended to add columns to ROOT dataframe representing MC, will add:

    - block: Representing block number, taken from file name
    '''
    # ---------------------------
    def __init__(self,
        sample_name : str,
        rdf         : RDF.RNode):
        '''
        sample_name: The name of the MC sample, needed to assign the block number, e.g. `mc_24_w31_34_magup_sim10d-splitsim02_11102202_bd_kstgamma_eq_highptgamma_dpc_ss_tuple`
        rdf_gen: ROOT dataframe with generator level candidates (MCDecayTree), by default None
        rdf_rec: ROOT dataframe with reconstructed candidates (DecayTree)
        '''
        self._sample_name = sample_name
        self._rdf         = rdf
        self._regex       = MC_REGEX 
        self._block_name  = 'block'
    # ---------------------------
    @cached_property
    def block(self) -> str:
        '''
        Associations taken from:

        https://lhcb-simulation.web.cern.ch/WPP/MCsamples.html#samples
        '''
        log.debug('Picking up blocks')

        mtch = re.match(self._regex, self._sample_name)
        if not mtch:
            raise ValueError(f'Cannot extract block identifier from sample: {self._sample_name}')

        identifier = mtch.group(1)

        if identifier == 'w31':
            return '1'

        if identifier == 'w32_34':
            return '2'

        if identifier == 'w25_27':
            return '4'

        if identifier == 'w35_37':
            return '5'

        if identifier == 'w37_39':
            return '6'

        if identifier == 'w40_41':
            return '7'

        if identifier == 'w41_42':
            return '8'

        raise ValueError(f'Invalid identifier: {identifier}')
    # ---------------------------
    def get_rdf(self) -> RDF.RNode:
        '''
        Returns dataframe after adding column
        '''
        rdf = self._rdf.Define(self._block_name, self.block)

        return rdf
# -----------------------------
