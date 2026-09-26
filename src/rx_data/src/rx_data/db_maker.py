'''
Module holding the DBMaker class
'''
import os

from functools    import cached_property
from dmu          import LogStore
from pydantic     import BaseModel
from dmu.generic  import Serializable
from dmu.generic  import Mode
from dmu.generic  import utilities as gut
from ROOT         import RDataFrame, RDF
from typing       import Final
from pathlib      import Path

from rx_data      import RDFGetter
from rx_common    import Qsq
from rx_common    import Cuts
from rx_common    import Trigger
from rx_common    import Component
from rx_selection import selection as sel

log=LogStore.add_logger('rx_data:db_maker')

_TREE_NAME : Final[str] = 'DecayTree' # Tree to be processed and saved
_Q2BIN     : Final[Qsq] = Qsq.central # Needed to select selection block from which to pick cut
# ------------------------
class DBMakerConf(BaseModel, Serializable, frozen = True):
    '''
    Class meant to configure DBMaker
    '''
    component    : Component
    trigger      : Trigger
    ncores       : int
    dropped_cuts : list[Cuts]
    # ------------------------
    @cached_property
    def columns(self) -> list[str]:
        '''
        List of columns to save
        '''
        data = gut.load_data(
            package = 'rx_data_data',
            fpath   = 'databases/fitter.yaml')

        return data['columns']
    # ------------------------
    @property
    def out_dir(self) -> Path:
        '''
        Path to directory where output goes
        '''
        anadir  = Path(os.environ['ANADIR'])
        out_dir = anadir / f'DB/fitter/{self.component}/{self.trigger.name}'

        out_dir.mkdir(exist_ok = True, parents = True)

        return out_dir
# ------------------------
class DBMaker:
    '''
    Class meant to:

    - Load data from ROOT files
    - Apply preselection and trimming
    - Save data to ROOT files
    '''
    # -----------------------------
    def __init__(self, cfg : DBMakerConf):
        '''
        Parameters
        -------------
        cfg: Object holding configuration
        '''
        self.__cfg      = cfg
        self.__out_path = self.__cfg.out_dir / 'data.root'
    # -----------------------------
    def __get_rdf(self) -> RDF.RNode:
        '''
        Returns ROOT dataframe associated to sample
        '''
        log.info('Loading dataframe')

        gtr = RDFGetter(
            tree   = _TREE_NAME,
            trigger= self.__cfg.trigger,
            sample = self.__cfg.component)

        rdf = gtr.get_rdf(per_file = False)

        return rdf
    # -----------------------------
    def __filter(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ---------------
        rdf: DataFrame before selection

        Returns
        ---------------
        Dataframe after selection
        '''
        log.info('Applying selection')
        overriding_cuts = { cut : 'true' for cut in self.__cfg.dropped_cuts }

        with sel.custom_selection(d_sel = overriding_cuts):
            rdf = sel.apply_full_selection(
                q2bin   = _Q2BIN,
                trigger = self.__cfg.trigger,
                process = self.__cfg.component,
                out_path= self.__cfg.out_dir,
                rdf     = rdf)

        return rdf
    # -----------------------------
    def __save(self, rdf : RDF.RNode) -> None:
        '''
        Parameters
        --------------
        rdf: Dataframe after selection
        '''
        found_columns = [ name.c_str() for name in rdf.GetColumnNames() ]
        columns       = [ name         for name in found_columns if name in self.__cfg.columns ]
        ncol          = len(columns)

        columns_path = self.__out_path.parent / 'columns.json'
        gut.dump_json(data = columns, path = columns_path)

        log.info(f'Saving {ncol} columns to: {self.__out_path}')
        rdf.Snapshot(
            treename  = _TREE_NAME,
            filename  = str(self.__out_path),
            columnList= columns)
    # -----------------------------
    def __rdf_from_db(self) -> RDF.RNode:
        '''
        Returns dataframe read from disk with `d_sel` attached with
        selection
        '''
        log.info(f'Reading file from: {self.__out_path}')
        rdf = RDataFrame(_TREE_NAME, str(self.__out_path))

        json_path = self.__out_path.parent / 'cuts.json'
        d_sel     = gut.load_json(path = json_path)

        setattr(rdf, 'd_sel', d_sel) # noqa: B010

        return rdf
    # -----------------------------
    def run(self, mode : Mode) -> RDF.RNode:
        '''
        Triggers execution
        '''
        mode.validate(path = self.__out_path)

        if mode == Mode.read:
            return self.__rdf_from_db()

        rdf = self.__get_rdf()
        rdf = self.__filter(rdf)

        self.__save(rdf = rdf)

        return rdf
# ------------------------
