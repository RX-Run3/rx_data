'''
Module with Stats class
'''
from ROOT        import RDF
from dmu         import LogStore
from rx_common   import Component, Trigger
from .spec_maker import SpecMaker

log=LogStore.add_logger('rx_data:stats')
# ----------------------------------------
class Stats:
    '''
    Class meant to provide number of candidates
    '''
    # ----------------------------------------
    def __init__(self, sample : Component, trigger : Trigger):
        '''
        sample  (str): MC sample identifier
        trigger (str): HLT2 trigger
        '''
        self._sample  = sample
        self._trigger = trigger
    # ----------------------------------------
    def get_entries(self, tree : str) -> int:
        '''
        Takes tree name, returns number of entries
        '''
        mkr = SpecMaker(
            component  = self._sample,
            trigger = self._trigger,
            tree    = tree)
        json_path = mkr.get_spec_path(per_file=False)

        rdf    = RDF.Experimental.FromSpec(str(json_path))
        val    = rdf.Count().GetValue()

        return val
# ----------------------------------------
