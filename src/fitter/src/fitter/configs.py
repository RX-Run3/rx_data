'''
Module containing classes representing configurations used for fitting
'''
import os
import copy

from functools   import cached_property
from pydantic    import BaseModel, field_validator, model_validator
from pathlib     import Path
from typing      import TYPE_CHECKING, Any, Callable, Literal, Self, Sequence
from rx_common   import MVAWp, Brem
from rx_common   import Channel, Mass, Project, Qsq, MisID, Region
from rx_common   import Component, Trigger, CCbarComponent, Cuts
from rx_misid    import MisIDSampleWeights
from dmu         import LogLevels, LogStore
from dmu.stats   import ModelFactoryConf
from dmu.stats   import KDEConf
from dmu.stats   import FitConf
from dmu.stats   import ZFitPlotterConf
from dmu.stats   import YieldsConf
from dmu.stats   import zfit
from dmu.generic import hashing
from dmu.generic import UnpackerModel

from .ccbar_conftf   import CCbarConfTF
from .component_conf import ComponentConf, ObservableConf
from .types          import CCbarWeight
from .toy_maker      import ToyConf

log = LogStore.add_logger('fitter:configs')

type zobs = zfit.Space
type zpdf = zfit.pdf.BasePDF
type zsum = zfit.pdf.SumPDF
type zpar = zfit.param.Parameter
# ------------------------------
def _validate_mod_cfg(value) -> 'FitModelConf | None':
    '''
    Validates that `value` is a FitModelConf or None, needed because of:

    https://github.com/pydantic/pydantic/issues/7713
    '''
    if value is None:
        return None

    if isinstance(value, FitModelConf):
        return value

    if isinstance(value, dict):
        return FitModelConf(**value)

    raise ValueError('Invalid value for mod_cfg field')
# ------------------------------
# Constraints
# ------------------------------
class ConstraintsCfg(UnpackerModel, frozen = True):
    '''
    Class meant to configure constraints
    '''
    signal_fraction : list[Component]
    combinatorial   : bool
    signal_shape    : bool
    if TYPE_CHECKING:
        misid : 'FitModelConf | None' = None
    else:
        misid : Any = None
    # --------------------------------------
    @field_validator('misid')
    @classmethod
    def _validate(cls, value : 'FitModelConf | None') -> 'FitModelConf | None':
        return _validate_mod_cfg(value = value)
    # ---------------------
    @classmethod
    def default(cls) -> 'ConstraintsCfg':
        '''
        Returns
        -------------
        Default configuration, mostly needed for tests
        '''
        return cls(
            combinatorial   = True,
            signal_shape    = True,
            signal_fraction = [])
    # ---------------------
    @property
    def is_empty(self) -> bool:
        '''
        True if no constraints are present
        '''
        return self.misid is None and self.signal_fraction is None
# ------------------------------
# Components
# ------------------------------
class CategoryConf(BaseModel):
    '''
    Class meant to configure a fit category
    '''
    selection : dict[Cuts,str]
    model     : ModelFactoryConf
# ------------------------------
class CCbarConf(ComponentConf, frozen = True):
    '''
    Class mean to control configuration to fit ccbar components
    '''
    samples : list[CCbarComponent]
    weights : dict[CCbarWeight,bool]
    merged  : dict[Qsq,bool]
    fit     : dict[Qsq, KDEConf]
    plots   : ZFitPlotterConf

    from_sim_fit : Literal[True] = True
    # -----------------
    def __str__(self):
        samples = [ f'{sample}' for sample in self.samples ] 
        weights = ''
        for key, val in self.weights.items():
            weights += f'{key:<20}{val}\n'

        msg = f'''
        Samples
        ----------------
        {samples}
        
        Weights
        ----------------
        {weights}
        
        Fit
        ----------------
        {self.fit}
        
        Plot
        ----------------
        {self.plots}'
        '''

        return msg.lstrip()
    # -----------------
    @classmethod
    def default(
        cls,
        channel : Channel) -> Self:
        '''
        Returns
        -----------
        Default instance of config, used for tests
        '''
        cfg_obs = ObservableConf.default()
        samples = Component.inclusive(channel = channel)
        weights = {
            CCbarWeight.dec : True,
            CCbarWeight.sam : True,
        }

        return cls(
            cfg_obs = cfg_obs,
            samples = samples,
            weights = weights,
            merged  = { qsq : False             for qsq in Qsq.for_physics() },
            fit     = { qsq : KDEConf.default() for qsq in Qsq.for_physics() },
            plots   = ZFitPlotterConf.default(),
        )
# ------------------------------
class ParametricConf(ComponentConf, frozen = True):
    '''
    Class mean to control configuration of fit to parametric models
    '''
    component  : Component
    fit        : FitConf
    categories : dict[str, CategoryConf]
    plots      : ZFitPlotterConf

    from_sim_fit : Literal[True] = True
    # ----------------------
    def filter_category(self, func : Callable[[str],bool]) -> Self:
        '''
        Parameters
        -------------
        func: Callable taking category name and returning true or false

        Returns
        -------------
        Copy of input config with categories filtered
        '''
        new_categories = { name : cat for name, cat in self.categories.items() if func(name) }

        return self.model_copy(update = {'categories' : new_categories})
    # ------------------------------
    def add_category_suffix(self, suffix : str) -> None:
        '''
        Needed to repurpose generic category, e.g. brem_xx1 -> brem_xx1_b1
        will allow using brem_xx1 for block 1

        Parameters
        ---------------
        suffix: String that will be added as suffix to key of categories, e.g. b1
        '''
        old_categories : list[str] = list(self.categories)
        new_categories : dict[str,CategoryConf] = dict()
        for name, cat in self.categories.items():
            new_categories[f'{name}_{suffix}'] = cat

        for name in old_categories:
            del self.categories[name]

        for key, val in new_categories.items():
            self.categories[key] = val
    # ----------------------
    def cfg_clone(
        self, 
        prefix: str, 
        brems : list[Brem]) -> Self:
        '''
        Parameters
        ---------------
        prefix : Initial part of category's original name
        brems  : List of signal brem categories for which prefixed section will be cloned 

        Returns
        ---------------
        Configuration with _cloned_ sections one for each
        brem category, with selections updated
        '''
        new_categories : dict[str,CategoryConf] = dict()
        log.debug('Clonning categories')
        for name, category in self.categories.items():
            if not name.startswith(prefix):
                raise ValueError(f'Category {name} does not start with prefix {prefix}')

            cloned_categories : dict[str,CategoryConf] = dict()
            for brem in brems:
                new_name = name.replace(prefix, str(brem))
                log.debug(f'{name:<20}{new_name:<20}')
                sel = category.selection.copy()
                sel.update(brem.selection)

                cloned_categories[new_name] = category.model_copy(
                    update = {'selection' : sel})

            new_categories.update(cloned_categories)

        return self.model_copy(update = {'categories' : new_categories})
    # ----------------------
    def cfg_copy(self, replacements : dict[str,str]) -> Self:
        '''
        This method provides a copy of the configuration with the
        categories renamed

        Parameters
        -----------------
        replacements: Dictionary where key is the the substring to be replaced
        and value is the replacement

        Returns
        -----------------
        Copy of config with renaming
        '''
        new_categories : dict[str,CategoryConf] = {}
        for name, conf in self.categories.items():
            new_name = name
            for old, new in replacements.items():
                new_name = name.replace(old, new)

            new_categories[new_name] = conf.model_copy()

        return self.model_copy(update = {'categories' : new_categories})
    # ----------------------
    def pick_category(self, name : str) -> Self:
        '''
        Parameters
        -----------------
        name: Name of category to pick

        Returns
        -----------------
        Copy of config with only that category
        '''
        new_categories : dict[str,CategoryConf] = {}
        for cat_name, conf in self.categories.items():
            if cat_name != name:
                continue

            new_categories[cat_name] = conf

        if not new_categories:
            for cat_name in self.categories:
                log.error(cat_name)
            raise ValueError(f'No category found for {self.component} with name: {name}')

        return self.model_copy(update = {'categories' : new_categories})
# ------------------------------
class NonParametricConf(ComponentConf, frozen = True):
    '''
    Class mean to control configuration of fit to non parametric models

    Attributes
    -------------------
    component    : MC sample used to build KDE
    fit          : Fit configuration for KDE
    plots        : Configuration for plotting
    events_range : Range where data will be taken from to build KDE
    '''
    component    : Component
    fit          : KDEConf
    plots        : ZFitPlotterConf
    events_range : tuple[int,int]
    from_sim_fit : Literal[True] = True 
    # ---------------------------
    @property
    def obs(self) -> zobs:
        '''
        Returns
        ----------------
        Observable used to build KDE
        '''
        if self.cfg_obs is None:
            raise ValueError('Observable configuration not set')

        obs = zfit.Space(
            obs   = 'Mass',
            label = self.cfg_obs.name,
            limits= self.events_range)

        return obs
    # ---------------------------
    @property
    def norm(self) -> zobs:
        '''
        Returns
        ----------------
        Observable where KDE is normalized to 1
        '''
        if self.cfg_obs is None:
            raise ValueError('Observable configuration not set')

        return self.cfg_obs.obs
# ------------------------------
class CmbConstraintConf(BaseModel, frozen = True):
    '''
    Class meant to represent configuration for combintorial constraints

    Attributes
    ---------------
    selection : Selection that sample will go through on top of nominal selection, e.g. vetos
    parameters: Parameters that will be constrained
    '''
    parameters : dict[Qsq,list[str]]
    if TYPE_CHECKING:
        mod_cfg : 'FitModelConf'
    else:
        mod_cfg : Any
    # --------------------------------------
    @field_validator('mod_cfg')
    @classmethod
    def _validate(cls, value : 'FitModelConf') -> 'FitModelConf':
        validated_value = _validate_mod_cfg(value = value)

        if validated_value is None:
            raise ValueError('mod_cfg field is None')

        return validated_value
    # --------------------------------------
    def specialize(self, q2bin : Qsq) -> Self:
        '''
        Parameters
        --------------
        q2bin: E.g. central

        Returns
        --------------
        Copy of current config for given q2 bin
        '''
        mod_cfg = self.mod_cfg.specialize(q2bin = q2bin)

        return self.model_copy(update = {'mod_cfg' : mod_cfg})
# ------------------------------
class CombinatorialConfUnconstrained(ComponentConf, frozen = True):
    '''
    Class mean to control configuration of fit to combinatorial
    for fits to control region, used to get constraints. I.e. 
    this fit has no constraints for the combinatorial, because
    here is where the constraints come from
    '''
    models      : dict[Qsq, ModelFactoryConf ]
    constraints : Literal[None] 
    from_sim_fit: Literal[True] = True 
# ------------------------------
class CombinatorialConf(ComponentConf, frozen = True):
    '''
    Class mean to control configuration of fit to combinatorial
    '''
    models      : dict[Qsq, ModelFactoryConf ]
    constraints : CmbConstraintConf
    from_sim_fit: Literal[True] = True 
    # --------------------------------------
    def specialize(self, q2bin : Qsq) -> Self:
        '''
        Parameters
        --------------
        q2bin: E.g. central

        Returns
        --------------
        Copy of current config for given q2 bin
        '''
        constraints = self.constraints.specialize(q2bin = q2bin)

        return self.model_copy(update = {'constraints' : constraints})
# ------------------------------
class MisIDConf(NonParametricConf, frozen = True):
    '''
    Configuration needed to build MisID components
    '''
    trigger   : Trigger
    project   : Project
    weights   : MisIDSampleWeights
    data_fit  : FitConf
    selection : dict[Cuts,str]
    from_sim_fit: Literal[True] = True 
    '''
    Overriding selection to full selection, e.g. `pid == false`
    Selection gets implemented in form of weights
    '''
# ------------------------------
AnyModelConf = CombinatorialConf | CombinatorialConfUnconstrained | ParametricConf | CCbarConf | MisIDConf | NonParametricConf | CCbarConfTF
# ------------------------------
class PlotConf(BaseModel):
    merging : dict[Brem,      list[Brem]]
    regions : dict[Brem, ZFitPlotterConf]
    # -----------------------------
    @classmethod
    def default(cls) -> Self:
        '''
        Returns default config, useful for tests
        '''
        merging : dict[Brem,list[Region]] = {}
        brems = {Brem.one : ZFitPlotterConf.default()}

        return cls(
            merging = merging,
            regions = brems)
# ------------------------------
# Fits
# ------------------------------
class FitModelConf(UnpackerModel, frozen = True):
    '''
    Class representing fitting model

    Attributes
    --------------------
    yields   : Contains configurations to build yields for a fitting region/PDF, etc
    selection: Dictionary mapping signal region with selection used to create it
    '''
    trigger    : Trigger
    yields     : YieldsConf
    selection  : dict[Qsq, dict[Cuts,str]]
    '''
    Selection needed to override default full selection
    '''
    observable : dict[Qsq | MisID, ObservableConf]
    components : dict[Qsq, dict[Component, AnyModelConf]]
    plots      : dict[Qsq, PlotConf]
    constraints: ConstraintsCfg
    fit        : FitConf
    q2bin      : Qsq | None = None
    # ------------------------
    @classmethod
    def default(cls) -> 'FitModelConf':
        '''
        Returns default version of config
        used mainly for fits
        '''
        return cls(
            trigger     = Trigger.rk_ee_os,
            selection   = {},
            yields      = YieldsConf(root = {}),
            observable  = {Qsq.central : ObservableConf.default()},
            plots       = {Qsq.central : PlotConf.default()},
            components  = {},
            constraints = ConstraintsCfg.default(),
            fit         = FitConf.default())
    # ------------------------
    def specialize(self, q2bin : Qsq) -> Self:
        '''
        Parameters
        ------------
        q2bin: q2 bin for which this config will be used

        Returns
        ------------
        Config needed for actual fit
        '''
        cfg_obs        = self.observable[q2bin]
        qsq_components = self.components[q2bin]

        new_components : dict[Component, AnyModelConf] = {}
        for component, cfg_cmp in qsq_components.items():
            new_cfg = self._update_cfg_obs(cfg_obs = cfg_obs, cfg_cmp = cfg_cmp)
            new_val = cfg_cmp.model_copy(update = {'cfg_obs' : new_cfg })

            if isinstance(new_val, CombinatorialConf):
                new_val = new_val.specialize(q2bin = q2bin)

            new_components[component] = new_val

        self.components[q2bin] = new_components

        return self.model_copy(update = {'components' : self.components, 'q2bin' : q2bin})
    # ----------------------
    def _update_cfg_obs(
        self,
        cfg_cmp : AnyModelConf,
        cfg_obs : ObservableConf) -> ObservableConf:
        '''
        Parameters
        ----------------
        cfg_obs: Configuration for observable in fit to data
        cfg_cmp: Configuration for fit component

        Returns
        ----------------
        Configuration for observable of component
        '''
        # If fit is to DTF mass, all components should use DTF mass
        # when fitting MC
        if cfg_obs.name.is_dtf:
            return cfg_obs

        # If fit uses muon non-DTF, use default mass from DaVinci
        if self.trigger.is_muon:
            return cfg_obs.model_copy(update = {'name' : Mass.b})

        # If fit uses electron non-DTF AND parametric PDF 
        # use unsmeared mass
        if not isinstance(cfg_cmp, (NonParametricConf, CCbarConf)):
            return cfg_obs

        # If fit uses electron non-DTF AND non-parametric PDF
        # use smeared mass
        return cfg_obs.model_copy(update = {'name' : cfg_obs.name.smeared_version })
    # ----------------------
    @property
    def hash(self) -> str:
        '''
        Hash for current config
        '''
        string = self.model_dump_json()

        return hashing.hash_object(obj = string)
    # ----------------------
    @property
    def obs(self) -> zobs:
        '''
        Observable needed for specialized model config fit
        '''
        if self.q2bin is None:
            raise ValueError('Cannot access q2bin of unspecialized FitModelConf instance')

        cfg_obs = self.observable[self.q2bin]

        return cfg_obs.obs
    # ----------------------
    def cfg_clone(
        self, 
        prefix  : str, 
        q2bin   : Qsq,
        brems   : list[Brem]) -> Self:
        '''
        Parameters
        ---------------
        prefix: Initial part of category's original name
        brems : List of brem categories for which prefixed section will be cloned 

        Returns
        ---------------
        Configuration with _cloned_ sections one for each
        brem category, with selections updated
        '''
        qsq_components = self.components[q2bin]

        new_components : dict[Component, AnyModelConf] = {}
        for comp, conf in qsq_components.items():
            if not isinstance(conf, ParametricConf):
                new_conf = conf.model_copy()
            else:
                new_conf = conf.cfg_clone(prefix = prefix, brems = brems)

            new_components[comp] = new_conf

        new_qsq_components = { q2bin : new_components }

        return self.model_copy(update = {'components' : new_qsq_components })
# ------------------------------
# Full config
# ----------------------
class RXFitConfig(BaseModel):
    '''
    Class used to store configuration needed for fits
    '''
    name    : str
    group   : str        # E.g. toys, needed to name directory where fit outputs will go
    mva_cmb : MVAWp
    mva_prc : MVAWp
    q2bin   : Qsq

    mod_cfg : FitModelConf
    output_directory : Path   = Path('/tmp')
    ncores  : int             = 1
    block   : int             = -1
    ncores  : int             = 1
    log_lvl : int             = 20
    ntoys   : int             = 0
    toy_cfg : ToyConf |  None = None
    # ----------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'RXFitConfig':
        if self.ncores < 1:
            raise ValueError(f'Invalid number of cores: {self.ncores}')

        self.output_directory = self._get_output_directory()

        return self
    # ----------------------
    def model_post_init(self, _):
        '''
        This runs after initialization
        '''
        self._set_logs()
        self._initialize_toy_config()

        self.mod_cfg = self.mod_cfg.specialize(q2bin = self.q2bin)
    # ----------------------
    def _initialize_toy_config(self) -> None:
        if self.toy_cfg is None:
            return

        update : dict[str,Path | int] = {
            'output' : self.output_directory / 'toys', 
            'ntoys'  : self.ntoys}

        self.toy_cfg = self.toy_cfg.model_copy(update = update)

        log.info(f'Sending toys to: {self.output_directory}')
        log.info(f'Setting number of toys to: {self.ntoys}')
    # ----------------------
    def _set_logs(self) -> None:
        '''
        Will put classes in a given logging level
        '''
        TOOL_LEVEL = self.log_lvl

        if TOOL_LEVEL < LogLevels.info:
            DEPENDENCIES_LEVEL = TOOL_LEVEL
        else:
            DEPENDENCIES_LEVEL = 30

        LogStore.set_level('dmu:statistics:fitter'                , DEPENDENCIES_LEVEL)
        LogStore.set_level('dmu:workflow:cache'                   , DEPENDENCIES_LEVEL)
        LogStore.set_level('dmu:stats:utilities'                  , DEPENDENCIES_LEVEL)
        LogStore.set_level('dmu:stats:model_factory'              , DEPENDENCIES_LEVEL)
        LogStore.set_level('dmu:stats:gofcalculator'              , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_data:rdf_getter'                   , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_data:path_splitter'                , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_data:sample_emulator'              , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_data:spec_maker'                   , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_data:sample_patcher'               , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_efficiencies:efficiency_calculator', DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_selection:truth_matching'          , DEPENDENCIES_LEVEL)
        LogStore.set_level('rx_selection:selection'               , DEPENDENCIES_LEVEL)
        LogStore.set_level('dmu:stats:constraint_adder'           , DEPENDENCIES_LEVEL)
        # ---------
        LogStore.set_level('fitter:fit_config'                    ,         TOOL_LEVEL)
        LogStore.set_level('fitter:likelihood_factory'            ,         TOOL_LEVEL)
        LogStore.set_level('fitter:data_preprocessor'             ,         TOOL_LEVEL)
        LogStore.set_level('fitter:prec'                          ,         TOOL_LEVEL)
        LogStore.set_level('fitter:prec_scales'                   ,         TOOL_LEVEL)
        LogStore.set_level('fitter:constraint_reader'             ,         TOOL_LEVEL)
        LogStore.set_level('fitter:fit_rx_data'                   ,         TOOL_LEVEL)
    # ----------------------
    def save(self) -> None:
        '''
        Saves to JSON fit configuration in directory where data fit will be saved
        '''
        path = self.output_directory / 'config.json'
        log.info(f'Saving fit configuration to: {path}')

        string = self.model_dump_json(indent = 2)

        path.write_text(string)
    # ----------------------
    def cfg_copy(
        self, 
        q2bin        : Qsq,
        replacements : dict[str,str]) -> Self:
        '''
        This method provides a copy of the configuration with the
        categories associated to parametric components, renamed

        Parameters
        -----------------
        q2bin       : Value of q2bin for which this config is needed
        replacements: Dictionary where key is the the substring to be replaced
                      and value is the replacement

        Returns
        -----------------
        Copy of config with renaming and with all components sections dropped
        but the one for the q2bin requested
        '''
        new_qsq_components : dict[Component, AnyModelConf] = {}
        old_qsq_components = self.mod_cfg.components[q2bin]
        for comp, conf in old_qsq_components.items():
            if not isinstance(conf, ParametricConf):
                new_conf = conf.model_copy()
            else:
                new_conf = conf.cfg_copy(replacements = replacements )

            new_qsq_components[comp] = new_conf

        new_mod_cfg = self.mod_cfg.model_copy(update = {'components' : {q2bin : new_qsq_components}})

        return self.model_copy(update = {'mod_cfg' : new_mod_cfg})
    # ----------------------
    def cfg_clone(
        self, 
        prefix  : str, 
        q2bin   : Qsq,
        brems   : list[Brem]) -> Self:
        '''
        Parameters
        ---------------
        q2bin   : Value of q2bin for which this config is needed
        prefix  : Initial part of category's original name
        brems   : List of brem categories for which prefixed section will be cloned 

        Returns
        ---------------
        Configuration with _cloned_ sections one for each
        brem categories, with selections updated
        '''
        new_mod_cfg = self.mod_cfg.cfg_clone(
            prefix  = prefix, 
            q2bin   = q2bin,
            brems   = brems)

        return self.model_copy(update = {'mod_cfg' : new_mod_cfg})
    # ----------------------
    def pick_category(
        self, 
        q2bin: Qsq,
        name : str) -> Self:
        '''
        Parameters
        -----------------
        name: Name of single category, for parametric model to be picked

        Returns
        -----------------
        Copy of config with that category
        '''
        new_qsq_components : dict[Component, AnyModelConf] = {}
        old_qsq_components = self.mod_cfg.components[q2bin]

        for comp, conf in old_qsq_components.items():
            if not isinstance(conf, ParametricConf):
                new_qsq_components[comp] = conf.model_copy()
                continue

            try:
                new_conf = conf.pick_category(name = name)
            except ValueError as exc:
                raise ValueError(f'Cannot find category {name} for component {comp}') from exc

            new_qsq_components[comp] = new_conf

        new_components = copy.deepcopy(self.mod_cfg.components)
        new_components[q2bin] = new_qsq_components

        new_mod_cfg = self.mod_cfg.model_copy(update = {'components' : new_components})

        return self.model_copy(update = {'mod_cfg' : new_mod_cfg})
    # ----------------------
    # Cached properties
    # ----------------------
    @cached_property
    def cmb_cut(self) -> str:
        '''
        Returns
        -------------
        Cut used for combinatorial MVA
        '''
        return self.mva_cmb.get_cut(name = 'mva_cmb')
    # ----------------------
    @cached_property
    def prc_cut(self) -> str:
        '''
        Returns
        -------------
        Cut used for part-reco MVA
        '''
        return self.mva_prc.get_cut(name = 'mva_prc')
    # ----------------------
    @cached_property
    def block_cut(self) -> str:
        '''
        Returns
        -------------
        String used to select block, e.g. `block == 3`
        '''
        if self.block == -1:
            return '(1)'

        if self.block == 12: # noqa
            return  '(block == 1) || (block == 2)'

        if self.block == 78: # noqa
            return  '(block == 7) || (block == 8)'

        if self.block in [1, 2, 3, 4, 5, 6, 7, 8]:
            return f'block == {self.block}'

        raise ValueError(f'Invalid block {self.block}')
    # ----------------------
    @cached_property
    def brem_cut(self) -> str:
        '''
        Returns
        -------------
        Cut on nbrem, normally exclude brem 0 for electron and do nothing for muon
        '''
        if self.mod_cfg.trigger.channel == Channel.ee:
            return 'nbrem != 0'

        if self.mod_cfg.trigger.channel == Channel.mm:
            return 'nbrem == 0'

        raise ValueError(f'Invalid trigger: {self.mod_cfg.trigger}')
    # ----------------------
    @cached_property
    def overriding_selection(self) -> dict[Cuts,str]:
        '''
        Returns
        -------------
        Dictionary mapping cut name with expression
        Needed to override default selection
        '''
        selection : dict[Cuts,str] = {
            Cuts.block : self.block_cut,
            Cuts.brem  : self.brem_cut,
            Cuts.cmb   : self.cmb_cut,
            Cuts.prc   : self.prc_cut,
        }

        selection.update(self.mod_cfg.selection[self.q2bin])

        return selection
    # ----------------------
    @cached_property
    def is_electron(self) -> bool:
        '''
        Returns
        -------------
        True if using electron trigger, false otherwise
        '''
        return self.mod_cfg.trigger.is_electron
    # ----------------------
    @cached_property
    def fit_name(self) -> str:
        '''
        Builds fit identifier from MVA working points
        '''
        name = f'{self.mva_cmb.name}_{self.mva_prc.name}'

        return name
    # ----------------------
    def _get_output_directory(self) -> Path:
        '''
        Returns
        -----------------
        Directory WRT which the `output_directory` key in the fit config will be defined
        '''
        if not isinstance(self.block, int):
            raise ValueError(f'Block is not an int but {type(self.block)} = {self.block}')

        if self.block == -1:
            block_name = 'all'
        else:
            block_name = f'b{self.block}'

        trigger = self.mod_cfg.trigger

        ana_dir = Path(os.environ['ANADIR'])
        out_dir = ana_dir / 'fits/data' / self.group / f'{self.fit_name}_{block_name}'
        out_dir = out_dir / self.q2bin.kind / trigger.project / trigger.channel / self.q2bin

        log.debug(f'Using output directory: {out_dir}')

        out_dir.mkdir(parents = True, exist_ok = True)

        return out_dir
    # ----------------------
    def data_fit_directory(self, regions : Sequence[str]) -> Path:
        '''
        Parameters
        ------------------
        regions: Sequence of fitting regions, e.g. brem_xx1, brem_xx2

        Returns
        ------------------
        Directory where region directories go 
        '''
        regs = '_'.join(regions)

        return self.output_directory / Path(Component.data_24) / 'fit' / regs
    # ----------------------
    @cached_property
    def obs(self) -> zobs:
        '''
        Returns
        -------------
        Zfit observable
        '''
        return self.mod_cfg.obs
# ----------------------
