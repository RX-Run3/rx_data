'''
Module with AtrMgr class
'''

import os
import dmu.generic.utilities as gut

from typing import Any
from ROOT   import RDF
from dmu    import LogStore

#TODO:Skip attributes that start with Take< in a betterway
log = LogStore.add_logger('dmu:rdataframe:atr_mgr')
#------------------------
class AtrMgr:
    '''
    Class intended to store attributes of ROOT dataframes and attach them back after a Filtering, definition, redefinition, etc operation
    These operations create new dataframes and therefore drop attributes.
    '''
    #------------------------
    def __init__(self, rdf : RDF.RNode):
        self.d_in_atr : dict[str,Any] = dict()

        self._store_atr(rdf)
    #------------------------
    def _store_atr(self, rdf : RDF.RNode):
        self.d_in_atr = self._get_atr(rdf)
    #------------------------
    def _skip_attr(self, name : str) -> bool:
        if name.startswith('__') and name.endswith('__'):
            return True

        return False
    #------------------------
    def _get_atr(self, rdf : RDF.RNode) -> dict[str,Any]:
        l_atr = dir(rdf)
        d_atr = {}
        for atr in l_atr:
            if self._skip_attr(atr):
                continue

            val = getattr(rdf, atr)
            d_atr[atr] = val

        return d_atr
    #------------------------
    def add_atr(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Takes dataframe and adds back the attributes
        '''
        d_ou_atr = self._get_atr(rdf)

        key_in_atr = set(self.d_in_atr.keys())
        key_ou_atr = set(     d_ou_atr.keys())

        key_to_add = key_in_atr.difference(key_ou_atr)

        for key in key_to_add:
            val = self.d_in_atr[key]
            if key.startswith('Take<') and key.endswith('>'):
                continue

            log.info(f'Adding attribute {key}')
            setattr(rdf, key, val)

        return rdf
    #------------------------
    def to_json(self, json_path : str, exists_ok : bool) -> None:
        '''
        Saves the attributes inside current instance to JSON. Takes JSON path as argument
        '''
        json_dir = os.path.dirname(json_path)
        os.makedirs(json_dir, exist_ok=True)

        t_type   = (list, str, int, float)
        d_fl_atr = { key : val for key, val in self.d_in_atr.items() if isinstance(val, t_type) and isinstance(key, t_type) }

        gut.dump_json(d_fl_atr, json_path, exists_ok=exists_ok)
#------------------------
