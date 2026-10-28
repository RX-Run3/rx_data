'''
Module containing EfficiencyScanner class
'''
import pandas as pnd
import math

from typing        import Final
from functools     import cached_property
from pydantic      import BaseModel, ConfigDict, RootModel, model_validator
from pathlib       import Path
from ROOT          import RDF
from dmu           import LogStore
from dmu.workflow  import Cache
from rx_data       import RDFGetter
from rx_selection  import selection as sel
from rx_common     import Component, Cuts, Qsq, Trigger, WorkingPoint

log = LogStore.add_logger('rx_efficiencies:efficiency_scanner')

_MCDT : Final[str] = 'MCDecayTree'
_DT   : Final[str] = 'DecayTree'
# --------------------------------
class Efficiency(BaseModel):
    model_config = ConfigDict(frozen=True)

    gen : int
    sel : int
    wp  : WorkingPoint
    # ----------------------------------------
    def __str__(self) -> str:
        msg = f'''
        Gen: {self.gen}
        Sel: {self.sel}
        Eff: {self.val:.3g}
        Err: {self.err:.3g}
        '''

        return msg
    # --------------------------------
    @cached_property
    def val(self) -> float:
        '''
        Efficiency
        '''
        return self.sel / float(self.gen)
    # --------------------------------
    @cached_property
    def err(self) -> float:
        '''
        Efficiency error
        '''
        var = self.val * (1 - self.val) / self.gen

        return math.sqrt(var)
    # --------------------------------
    @property
    def row(self) -> dict[str,float]:
        '''
        Dictionary representing row in pandas dataframe
        '''
        data = dict()
        data['gen'] = self.gen
        data['sel'] = self.sel
        data['eff'] = self.sel / float(self.gen)
        for cut in self.wp.root:
            data[cut.cut] = cut.val

        return data
# --------------------------------
class EfficiencyGrid(RootModel[list[Efficiency]]):
    '''
    Class meant to represent a grid of efficiencies per working point
    '''
    # --------------------------------
    @property
    def df(self) -> pnd.DataFrame:
        '''
        Table with efficiencies for each working point
        made into a pandas dataframe 
        '''
        rows : list[dict[str,float]] = [ eff.row for eff in self.root ]

        return pnd.DataFrame(rows)
    # --------------------------------
    @classmethod
    def from_json(cls, path : Path) -> 'EfficiencyGrid':
        '''
        Parameters
        ---------------
        path: Path to JSON file with serialized object

        Returns
        ---------------
        Instance of efficiency grid
        '''
        string = path.read_text()

        return cls.model_validate_json(json_data = string)
    # --------------------------------
    @classmethod
    def from_rdf(cls, gen : RDF.RNode, rec : dict[WorkingPoint, RDF.RNode]) -> 'EfficiencyGrid':
        '''
        Parameters
        -------------------
        gen: Dataframe from MCDecayTree, i.e. with generator level data
        rec: Dictionary mapping working point to corresponding dataframe

        Returns
        -------------------
        Efficiency grid object
        '''
        nrec = len(rec)

        log.info(f'Calculating {nrec} efficiencies from dataframes')

        ngen  = gen.Count().GetValue()
        d_sel = { wp : rdf.Count().GetValue() for wp, rdf in rec.items() }

        log.info('Yields calculated')

        efficiencies = [ Efficiency(gen = ngen, sel = nsel, wp = wp) for wp, nsel in d_sel.items() ]

        log.info('Efficiencies calculated')

        return cls(root = efficiencies)
    # --------------------------------
    def to_json(self, path : Path) -> None:
        '''
        Parameters
        --------------
        path: Path to file where current instance will be saved as JSON
        '''
        string = self.model_dump_json(indent = 2)
        path.write_text(string)
# --------------------------------
class EfficiencyScannerConf(BaseModel):
    '''
    Class meant to configure EfficiencyScanner
    '''
    model_config = ConfigDict(frozen=True)
    # ---------------------------------
    sample  : Component
    trigger : Trigger
    q2bin   : Qsq
    wps     : list[WorkingPoint]
    # ---------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'EfficiencyScannerConf':
        all_vars = [ wp.variables for wp in self.wps ]
        all_cuts = [ wp.cuts      for wp in self.wps ]

        if not all(var == all_vars[0] for var in all_vars):
            raise ValueError('Not found one and only one set of variables across working points')

        if not all(var == all_cuts[0] for var in all_cuts):
            raise ValueError('Not found one and only one set of cuts across working points')

        return self
    # ---------------------------------
    @cached_property
    def cuts(self) -> list[Cuts]:
        '''
        Cuts used by all working points, all working points
        need to cut on the same quantities
        '''
        return self.wps[0].cuts
    # ---------------------------------
    @cached_property
    def name(self) -> str:
        '''
        Identifier for current scan, used for naming outputs
        '''
        return f'{self.sample}_{self.trigger}_{self.q2bin}'
    # ---------------------------------
    @cached_property
    def variables(self) -> list[str]:
        '''
        List of variables used for cuts
        '''
        return self.wps[0].variables
# --------------------------------
class EfficiencyScanner(Cache):
    '''
    Class meant to scan efficiencies in MC samples

    It will

    - Apply full selection, except for cuts involving variables been scanned
    - Scan those variables and provide dataframe with efficiencies
    '''
    # --------------------------------
    def __init__(self, cfg : EfficiencyScannerConf):
        '''
        Parameters
        ----------------
        cfg: Object needed to configure scan of efficiencies
        '''
        super().__init__(
            out_path= Path(cfg.name),
            cfg     = cfg.model_dump())

        self._cfg = cfg
    # --------------------------------
    def _check_rdf(self, rdf : RDF.RNode) -> None:
        '''
        Check that all variables we will scan exist in dataframe
        '''
        columns = [ var.c_str()                for var in rdf.GetColumnNames() ]
        # Drop prefix for variables in friend trees
        columns = [ var.c_str().split('.')[-1] for var in rdf.GetColumnNames() ]
        columns = sorted(columns)

        fail = False
        for variable in self._cfg.variables:
            if variable not in columns:
                log.error(f'Missing variable: {variable}')
                fail = True

        if fail:
            log.info(columns)
            raise ValueError('At least one variable was not found')
    # --------------------------------
    def _get_rdf(self, tree : str) -> RDF.RNode:
        '''
        Load dataframe and lazily apply selection, except for the scanning part

        Parameters
        ---------------------
        tree: DecayTree or MCDecayTree

        Returns
        ---------------------
        Dataframe
        '''
        log.debug('Getting dataframe')

        sample  = self._cfg.sample
        trigger = self._cfg.trigger

        gtr = RDFGetter(sample=sample, trigger=trigger, tree = tree)
        rdf = gtr.get_rdf(per_file = False)

        if tree == _MCDT:
            return rdf

        self._check_rdf(rdf=rdf)

        log.debug('Applying selection')

        custom_sel : dict[Cuts, str] = { cut : 'true' for cut in self._cfg.cuts }

        with sel.custom_selection(d_sel = custom_sel):
            rdf         = sel.apply_full_selection(
                rdf     = rdf,
                q2bin   = self._cfg.q2bin,
                process = self._cfg.sample,
                trigger = self._cfg.trigger,
                out_path= self.path)

        return rdf
    # --------------------------------
    def run(self) -> EfficiencyGrid:
        '''
        Runs calculation of efficiencies in grid of working points

        Returns
        ------------------
        EfficiencyGrid object
        '''
        out_path = self._out_path / 'efficiency.json'

        if self._copy_from_cache():
            log.info('Efficiencies cached, reloading them')
            obj = EfficiencyGrid.from_json(path = out_path)

            return obj

        log.info('Efficiencies not cached, calculating them')
        rdf_gen   = self._get_rdf(tree = _MCDT)
        rdf_rec   = self._get_rdf(tree = _DT  )

        d_rdf_rec : dict[WorkingPoint, RDF.RNode] = dict()
        for wp in self._cfg.wps:
            d_rdf_rec[wp] = wp.select(rdf = rdf_rec)

        obj = EfficiencyGrid.from_rdf(gen = rdf_gen, rec = d_rdf_rec)
        obj.to_json(path = out_path)

        self._cache()

        return obj
# --------------------------------
