'''
Module holding SampleEmulator class
'''

from ROOT        import RDF # type: ignore
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
    '''
    root : dict[str,float]
    # --------------------------------------
    def model_post_init(self, context) -> None:
        self._validate_sample()

        return super().model_post_init(context)
    # --------------------------------------
    def _validate_sample(self):
        if len(self.root) == 1:
            (name, frac), = self.root.items()
            if name == 'any' and frac == 1.0:
                return

        for name, fraction in self.root.items():
            self._validate_sample_name(name = name)

            if fraction < 0 or fraction > 1.0:
                raise ValueError(f'Invalid sample fraction {fraction:.3f} for {name}')
    # --------------------------------------
    def _validate_sample_name(self, name : str):
        try:
            Component.from_sample(sample = name)
        except Exception as exc:
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
        self._sample  = sample
        cfg       : DictConfig = gut.load_conf(package='rx_data_data', fpath='emulated_trees/config.yaml')
        self._cfg : DictConfig = cfg.get(sample, DictConfig({}))
    # ----------------------
    def _run_redefine(
        self, 
        rdf         : RDF.RNode, 
        definitions : DictConfig) -> RDF.RNode:
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

        if 'redefine' not in self._cfg:
            self._cfg['redefine'] = dict()

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

        if not self._cfg: 
            log.debug(f'Not emulating {self._sample}, missing in config')
            return rdf

        log.info(f'Emulating {self._sample}')

        if 'redefine' in self._cfg:
            rdf = self._run_redefine(rdf=rdf, definitions=self._cfg.redefine)
        else:
            log.debug('Not running redefinitions')

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
