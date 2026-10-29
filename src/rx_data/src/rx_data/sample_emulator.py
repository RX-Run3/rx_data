'''
Module holding SampleEmulator class
'''
import json

from ROOT        import RDF
from dmu         import LogStore
from typing      import Any
from dmu.generic import utilities as gut
from pydantic    import BaseModel, RootModel
from rx_common   import Block, Component 

log=LogStore.add_logger('rx_data:sample_emulator')
# ----------------------
class SamplesConf(RootModel[dict[Component,float]], frozen=True, strict=True):
    '''
    Class meant to represent a cocktail of samples
    and the fractions of each

    Attributes:
    ------------------
    root: Dictionary mapping sample name (e.g. Bs_JpsiKst_ee_eq_DPC) to
          fraction of it in cocktail
    '''
    # --------------------------------------
    def __str__(self):
        msg = '\n'
        msg+= 20 * '-' + '\n'
        msg+= 'Cocktail components\n'
        msg+= 20 * '-' + '\n'
        for component, fraction in self.root.items():
            msg += f'{component:<30}{fraction:.3g}\n'

        return msg
    # --------------------------------------
    @property
    def is_cocktail(self) -> bool:
        '''
        True if this is a set of samples instead of one
        '''
        return len(self.root) > 1
    # --------------------------------------
    @property
    def is_data(self) -> bool:
        '''
        True if all keys are data samples
        '''
        for component in self.root:
            if component.is_mc:
                return False

        return True
    # --------------------------------------
    def emulated_only_by(self, sample : str) -> bool:
        '''
        Parameters
        -------------
        sample: Name of MC sample

        Returns
        -------------
        True if current config describes `sample` as the only
        emulator sample
        '''
        if len(self.root) != 1:
            return False

        (emulator, frac), = self.root.items()

        if frac != 1:
            raise ValueError(f'Found single emulating sample with fraction: {frac}')

        return emulator == sample
    # --------------------------------------
    def model_post_init(self, context : Any) -> None:
        self.__validate_fraction()

        return super().model_post_init(context)
    # --------------------------------------
    def __validate_fraction(self):
        fractions = list(self.root.values())

        if not all(0.0 < fraction <= 1.0 for fraction in fractions):
            raise ValueError(f'Invalid sample fractions: {self}')

        if sum(fractions) != 1:
            raise ValueError(f'Sum of sample fractions not 1: {fractions}')
# ----------------------
class EmulationConf(BaseModel, frozen=True, extra='forbid', strict=True):
    '''
    Class meant to represent configuration needed
    to emulate a sample
    '''
    samples  : SamplesConf 
    patching : dict[Block, Block] = dict() 
    '''Dictionary meant to allow patching blocks of data'''

    redefine : dict[str  ,   str] = dict() 
    '''Dictionary used to update candidate information, e.g. B -> B + 30
    meant to change mass hypotheses of particles or mother IDs'''

    trk_swap : dict[str  ,   str] = dict()
    '''Dictionary mapping particle prefixes, e.g. L1 -> H
    meant to be used to swap values of columns'''
    # --------------------------------------
    def model_post_init(self, context : Any) -> None:
        '''
        Validates fields
        '''
        self._validate_patching()

        return super().model_post_init(context)
    # --------------------------------------
    def _validate_patching(self):
        for init, fnal in self.patching.items():
            if init == fnal:
                raise ValueError('Initial and final block cannot be the same')
# ----------------------
class EmulatorConf(RootModel[dict[Component, EmulationConf]], frozen=True, strict=True):
    '''
    Class meant to represent configuration needed to emulate
    samples
    '''
# ----------------------
class SampleEmulator:
    '''
    Class meant to:

    - Open config file with emulation settings
    - Provide emulating sample name 
    - Postprocess original sample to make it suitable for emulation
    '''
    # ----------------------
    def __init__(self, sample : Component) -> None:
        '''
        Parameters
        ---------------
        sample: Sample to emulate e.g. bpkpee 
        '''
        fpath       = 'emulated_trees/config.yaml'
        data        = gut.load_data(package='rx_data_data', fpath=fpath)
        data_string = json.dumps(data)
        cfg         = EmulatorConf.model_validate_json(data_string)

        if sample in cfg.root:
            log.warning(f'Emulating {sample}')
            self._cfg = cfg.root[sample]
            return

        log.info(f'Not emulating {sample}')
        samples   = SamplesConf({sample : 1.0})
        self._cfg = EmulationConf(samples = samples)
    # ----------------------
    def _run_redefine(
        self, 
        rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf : DataFrame before redefinitions

        Returns
        -------------
        Dataframe after definitiions
        '''
        for var, expr in self._cfg.redefine.items():
            assert isinstance(var, str)

            log.debug(f'{var:<10}{"--->"}\n{expr}')
            rdf = rdf.Redefine(var, expr)

        return rdf
    # ----------------------
    def _update_cocktail_weights(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: Dataframe
    
        Returns
        -------------
        Dataframe with cocktail weights added
        '''
        if not self._cfg.samples.is_cocktail:
            return rdf

        # TODO: Needs to be implemented when EVENTTYPE branch be fixed
        # Hard to pick correct weight per-sample otherwise
        log.warning(f'Not adding cocktail weights for: {self._cfg.samples}')

        return rdf
    # ----------------------
    def _swap_tracks(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        ----------------
        rdf: ROOT dataframe

        Returns
        ----------------
        Dataframe with track swapping, if requested through `trk_swap`
        '''
        if not self._cfg.trk_swap:
            return rdf

        cols = [ col.c_str() for col in rdf.GetColumnNames() ]

        for col_1, col_2 in self._cfg.trk_swap.items():
            rdf = self._swap_columns(rdf, cols, col_1, col_2)
            rdf = self._swap_columns(rdf, cols, col_2, col_1)

        return rdf
    # ----------------------
    def _swap_columns(
        self,
        rdf   : RDF.RNode,
        cols  : list[str],
        prf_1 : str,
        prf_2 : str) -> RDF.RNode:
        '''
        Parameters
        --------------
        rdf  : ROOT dataframe
        cols : All columns in dataframe
        prf_x: Column prefixes for columns to be swapped, e.g. L1, H

        Returns 
        --------------
        Dataframe with columns associated to prefix `prf_1` renamed to
        `prf_2`, `tmp_{prf_1}_...` columns will be added as byproduct.

        cols gets updated with `tmp_...` columns
        '''
        cols_1 = [ col for col in cols if col.startswith(prf_1) ]

        for col_1 in cols_1:
            tmp   = f'tmp_{col_1}'
            stem  = col_1.removeprefix(prf_1)
            col_2 = f'{prf_2}{stem}'
            col_2 = col_2 if f'tmp_{col_2}' not in cols else f'tmp_{col_2}'

            if col_2 not in cols:
                log.warning(f'Cannot find {col_2} for swapping')
                continue

            rdf = rdf.Define(tmp, col_1)
            cols.append(tmp)

            if col_1 in cols:
                rdf = rdf.Redefine(col_1, col_2)
            else:
                rdf = rdf.Define(col_1, col_2)
                cols.append(tmp)

        return rdf
    # ---------------------
    @property
    def samples(self) -> SamplesConf:
        '''
        Object specifying how to build sample passed in initializer
        '''
        return self._cfg.samples
    # ----------------------
    def post_process(self, rdf : RDF.RNode) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf: ROOT dataFrame

        Returns
        -------------
        Dataframe after redefinitions, etc
        '''
        size = rdf.Count().GetValue()
        if size == 0:
            log.warning('Not running emulation for empty dataframe')
            return rdf

        rdf = self._run_redefine(rdf=rdf)
        rdf = self._update_cocktail_weights(rdf = rdf)
        rdf = self._swap_tracks(rdf=rdf)

        return rdf
# ----------------------
