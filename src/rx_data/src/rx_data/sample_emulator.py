'''
Module holding SampleEmulator class
'''

from ROOT        import RDF
from dmu         import LogStore
from dmu.generic import utilities as gut
from pydantic    import BaseModel, RootModel
from rx_common   import Block, Component 

log=LogStore.add_logger('rx_data:sample_emulator')
# ----------------------
class SamplesConf(RootModel):
    '''
    Class meant to represent a cocktail of samples
    and the fractions of each

    Attributes:
    ------------------
    root: Dictionary mapping sample name (e.g. Bs_JpsiKst_ee_eq_DPC) to
          fraction of it in cocktail
    '''
    root : dict[Component,float]
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
    def model_post_init(self, context) -> None:
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
class EmulationConf(BaseModel):
    '''
    Class meant to represent configuration needed
    to emulate a sample
    '''
    samples  : SamplesConf 
    patching : dict[Block, Block] = dict() 
    redefine : dict[str  ,   str] = dict() 
    # --------------------------------------
    def model_post_init(self, context) -> None:
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
class EmulatorConf(RootModel):
    '''
    Class meant to represent configuration needed to emulate
    samples
    '''
    root : dict[Component,EmulationConf]
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
        fpath= 'emulated_trees/config.yaml'
        data = gut.load_data(package='rx_data_data', fpath=fpath)
        cfg  = EmulatorConf(**data)

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
        rdf         : RDF.RNode, 
        definitions : dict[str,str]) -> RDF.RNode:
        '''
        Parameters
        -------------
        rdf : DataFrame before redefinitions
        definitions: Dictionary between variable and new definition

        Returns
        -------------
        Dataframe after definitiions
        '''
        for var, expr in definitions.items():
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
    def extend_redefinitions(self, redefinitions : dict[str,str]) -> None:
        '''
        Add extra entries to redefinition section of config

        Parameters
        -------------
        redefinitions: Dictionary mapping column name to new definition

        Raises 
        -------------
        ValueError: If a column re-definition is already present in config
        '''
        if not redefinitions:
            log.info('Not using extra redefinitions')
            return

        fail = False
        log.info('Extending columns redefinitions')
        for name, expr in redefinitions.items():
            log.debug(f'{name:<20}{expr}')

        for name, expression in redefinitions.items():
            if name in self._cfg.redefine:
                log.error(f'Cannot redefine {name}, already in redefine block')
                fail = True
                continue

            log.debug(name)
            self._cfg.redefine[name] = expression

        if fail:
            raise ValueError('Cannot redefine, some columns are already found in config')
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

        rdf = self._run_redefine(rdf=rdf, definitions=self._cfg.redefine)
        rdf = self._update_cocktail_weights(rdf = rdf)

        return rdf
    # ---------------------
    def get_samples(self) -> SamplesConf:
        '''
        Returns
        -------------
        Object specifying how to build sample passed in initializer
        '''
        return self._cfg.samples
# ----------------------
