'''
Module holding DatabaseBuilder and its config
'''
import pandas as pnd

from typing         import Final
from rx_selection   import selection as sel
from ROOT           import RDF
from rx_common      import Trigger, Component, Qsq
from dmu            import LogStore
from rx_data        import RDFGetter

from .database_conf import DatabaseConf

log=LogStore.add_logger('hqm:database_builder')

_DUMMY_QSQ : Final[Qsq] = Qsq.jpsi # Won't apply q2 cut, need placeholder
# ----------------------
class DatabaseBuilder:
    '''
    Class meant to create parquet files with data needed by
    DataStore
    '''
    # ----------------------------------
    def __init__(
        self,
        cfg : DatabaseConf,
        trig: Trigger,
        comp: Component):
        '''
        Parameters
        ----------------
        cfg : Config object
        trig: Hlt2 trigger
        comp: Sample used to read data from
        '''
        self._cfg = cfg.update_columns(is_mc = comp.is_mc)
        self._trig= trig
        self._comp= comp
    # ----------------------------------
    def __get_rdf(self) -> RDF.RNode:
        '''
        Returns ROOT dataframe
        '''
        log.debug(f'Picking up dataframe for: {self._trig}/{self._comp}')

        gtr        = RDFGetter(
            trigger= self._trig,
            sample = self._comp)

        rdf  = gtr.get_rdf(per_file = False)
        path = self._cfg.get_path(
            comp = self._comp,
            trig = self._trig)

        with sel.custom_selection(d_sel = self._cfg.selection):
            rdf = sel.apply_full_selection(
                rdf     = rdf,
                q2bin   = _DUMMY_QSQ,
                process = self._comp,
                trigger = self._trig,
                out_path= path.parent)

        return rdf
    # ----------------------------------
    def __validate_columns(self, rdf : RDF.RNode) -> None:
        cols = rdf.GetColumnNames()
        fail = False
        for col in self._cfg.columns:
            if col not in cols:
                fail = True
                log.error(col)

        if fail:
            raise ValueError('At least one column was not found in dataframe')

        log.debug('ROOT dataframe validated')
    # ----------------------------------
    def _rename_variable(self, var : str) -> str:
        '''
        Renames variables like `mva.mva_cmb` to `mva_cmb`
        '''
        if '.' not in var:
            return var

        return var.split('.')[-1]
    # ----------------------------------
    def run(self) -> None:
        '''
        Execute building of database
        '''
        rdf = self.__get_rdf()
        self.__validate_columns(rdf = rdf)

        data = rdf.AsNumpy(self._cfg.columns)
        data = { self._rename_variable(var) : val for var, val in data.items() }
        df   = pnd.DataFrame(data)

        path = self._cfg.get_path(
            trig = self._trig,
            comp = self._comp)

        log.debug('Using columns:')
        for name in df.columns:
            log.debug(name)

        log.info(f'Saving to: {path}')
        df.to_parquet(path = path)
# ----------------------
