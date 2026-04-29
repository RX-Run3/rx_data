'''
Module holding SampleEmulator class
'''

from fnmatch     import fnmatch
from ROOT        import RDF # type: ignore
from dmu         import LogStore
from dmu.generic import utilities as gut
from pydantic    import BaseModel, RootModel
from rx_common   import Block, Component 
from rx_common   import MissingComponent

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
    root : dict[str,float]
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
        for sample in self.root:
            if Component.from_sample(sample = sample).is_mc:
                return False

        return True
    # --------------------------------------
    def contains(self, sample : str) -> bool:
        '''
        Parameters
        ---------------
        sample: E.g. Bs_JpsiKst_ee_eq_DPC

        Returns
        ---------------
        True if `sample` is in dictionary
        '''
        if sample in self.root:
            return True

        try:
            comp = Component.from_sample(sample = sample)
        except MissingComponent:
            # If cannot find sample, then it's MC (real data should always
            # be associated to component)
            # If MC and not found in config, skip sample 
            return False

        # If MC and not found skip
        if comp.is_mc:
            return False

        # ---------
        # Below this point `sample` is real data
        # ---------

        # If sample did not match, root is wildcard
        # and a single wildcard 
        if len(self.root) != 1:
            return False

        (pattern, _), = self.root.items()

        # If matches pattern, pick
        return fnmatch(name = sample, pat = pattern)
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
        self.__validate_sample()
        self.__validate_fraction()

        return super().model_post_init(context)
    # --------------------------------------
    def __validate_fraction(self):
        fractions = list(self.root.values())

        if sum(fractions) != 1:
            raise ValueError(f'Sum of sample fractions not 1: {fractions}')
    # --------------------------------------
    def __validate_sample(self):
        if len(self.root) == 1:
            (name, frac), = self.root.items()
            if name == 'any' and frac == 1.0:
                return

        for name, fraction in self.root.items():
            self.__validate_sample_name(name = name)

            if fraction < 0 or fraction > 1.0:
                raise ValueError(f'Invalid sample fraction {fraction:.3f} for {name}')
    # --------------------------------------
    def __validate_sample_name(self, name : str):
        try:
            Component.from_sample(sample = name)
        except MissingComponent as exc:
            raise ValueError(f'No component associated to sample: {name}') from exc
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
    root : dict[str,EmulationConf]
# ----------------------
class SampleEmulator:
    '''
    Class meant to:

    - Open config file with emulation settings
    - Provide emulating sample name 
    - Postprocess original sample to make it suitable for emulation
    '''
    # ----------------------
    def __init__(self, sample : str) -> None:
        '''
        Parameters
        ---------------
        sample: Name of sample to emulate, e.g. Bs_JpsiKst_ee_eq_DPC
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
        Dictionary after definitiions
        '''
        for var, expr in definitions.items():
            assert isinstance(var, str)

            log.debug(f'{var:<30}{"--->"}{expr:<}')
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
