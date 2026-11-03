'''
Module with RDFRenamer
'''
from typing import Final
from ROOT   import RDF
from dmu    import LogStore

log=LogStore.add_logger('rx_data:rdf_renamer')

# When dropping dots from branches associated to friend trees
# skip these branches
_SKIP_TARGETS : Final[list[str]] = ['EVENTNUMBER', 'RUNNUMBER']
# ----------------------
class RDFRenamer:
    '''
    Class meant to rename dataframe branches
    '''
    # -----------------------------
    def __alias_from_dotted(self, name : str) -> str:
        '''
        Parameters
        -------------
        name: Name of column associated to friend tree

        Returns
        -------------
        Name of branch to be used as alias, e.g. friend.[ALIAS_NAME]
        '''
        try:
            [friend, column] = name.split('.')
        except Exception as exc:
            raise ValueError(f'Cannot split {name} into friend and column names') from exc

        return column
    # -----------------------------
    def __alias_friend_branches(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ------------------
        rdf: Dataframe from RDFGetter

        Returns
        ------------------
        Dataframe with friend tree branches aliased, e.g. mva.mva_cmb -> mva_cmb
        '''
        columns = [ name.c_str() for name in rdf.GetColumnNames() ]
        renaming= { name : self.__alias_from_dotted(name = name) for name in columns if '.' in name }

        fail = False
        for source, target in renaming.items():
            if target in _SKIP_TARGETS:
                continue

            if target in columns:
                fail = True
                for col in columns:
                    if col.endswith(target):
                        log.error(col)
                log.error('')

                continue

            rdf = rdf.Redefine(target, source)

        if fail:
            raise ValueError('Cannot rename dotted columns')

        return rdf
    # -----------------------------
    def run(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        --------------
        rdf: ROOT dataframe before renaming

        Returns
        --------------
        ROOT dataframe after renaming
        '''
        rdf = self.__alias_friend_branches(rdf = rdf)

        return rdf
# ----------------------
