'''
Module holding DatabaseBuilder and its config
'''
import os
import pandas as pnd

from typing       import Final
from rx_selection import selection as sel
from pathlib      import Path
from ROOT         import RDF # type: ignore 
from pydantic     import BaseModel
from rx_common    import Cuts, Trigger, Component, Qsq
from dmu          import LogStore
from dmu.generic  import utilities as gut
from rx_data      import RDFGetter

log=LogStore.add_logger('hqm:database_builder')

_DUMMY_QSQ : Final[Qsq] = Qsq.jpsi # Won't apply q2 cut, need placeholder
# ----------------------
class DatabaseBuilderConf(BaseModel):
    '''
    Class meant to hold configuration for DatabaseBuilder
    '''
    selection: dict[Cuts, str]
    columns  : list[str]
    db_dir   : Path
    # ----------------------
    def get_path(self, comp : Component, trig : Trigger) -> Path:
        '''
        Parameters
        --------------
        comp: Denotes sample where path will go/be read
        trig: Hlt2 trigger

        Returns
        --------------
        Path to parquet file with data
        '''
        anadir = Path(os.environ['ANADIR'])
        path   = anadir / self.db_dir / f'{comp}_{trig}.parquet'
        path.parent.mkdir(parents = True, exist_ok = True)

        return path
    # ----------------------
    @classmethod
    def load(cls) -> 'DatabaseBuilderConf':
        data = gut.load_data(package = 'hqm_data', fpath = 'config/database_builder.yaml')

        return cls(**data)
# ----------------------
class DatabaseBuilder:
    '''
    Class meant to create parquet files with data needed by
    DataStore
    '''
    # ----------------------------------
    def __init__(
        self, 
        cfg : DatabaseBuilderConf,
        trig: Trigger,
        comp: Component):
        '''
        Parameters
        ----------------
        cfg : Config object
        trig: Hlt2 trigger
        comp: Sample used to read data from
        '''
        self._cfg = cfg
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
    def run(self) -> None:
        '''
        Execute building of database
        '''
        rdf = self.__get_rdf()
        self.__validate_columns(rdf = rdf)

        data = rdf.AsNumpy(self._cfg.columns)

        df = pnd.DataFrame(data)

        path = self._cfg.get_path(
            trig = self._trig, 
            comp = self._comp)

        log.info(f'Saving to: {path}')
        df.to_parquet(path = path)
# ----------------------
