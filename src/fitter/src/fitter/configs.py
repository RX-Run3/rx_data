'''
Module containing classes representing configurations used for fitting
'''
import os

from functools   import cached_property
from pydantic    import BaseModel, ConfigDict
from pathlib     import Path
from typing      import Callable, Self

from rx_common   import Channel, Mass, Project, Qsq, MisID
from rx_common   import Component, Trigger, CCbarComponent, Cuts
from rx_misid    import MisIDSampleWeights
from dmu         import LogLevels, LogStore
from dmu.stats   import ModelFactoryConf
from dmu.stats   import KDEConf
from dmu.stats   import FitConf
from dmu.stats   import ZFitPlotterConf
from dmu.stats   import YieldsConf
from dmu.stats   import zfit
from dmu.generic import UnpackerModel
from zfit        import Space      as zobs

from .mva_conf   import MVAWp
from .types      import CCbarWeight
from .toy_maker  import ToyConf

log=LogStore.add_logger('fitter:configs')
# ------------------------------
class ObservableConf(BaseModel):
    '''
    Class representing configuration for observable
    '''
    model_config = ConfigDict(frozen=True)

    name : Mass
    range: tuple[int,int]
    # ------------------------
    def __str__(self):
        lower, upper = self.range

        val = '\n------------------------\n'
        val+= f'Observable: {self.name}\n'
        val+= f'Range     : [{lower}, {upper}]\n'
        val+= '------------------------'

        return val
    # ------------------------
    @classmethod
    def default(cls) -> Self:
        '''
        Returns
        -------------
        Default instance of observable config
        needed for tests
        '''
        return cls(name = Mass.bp_bcor, range = (4500, 7000))
# ------------------------------
# Constraints
# ------------------------------
class ConstraintsCfg(UnpackerModel):
    '''
    Class meant to configure constraints
    '''
    model_config = ConfigDict(frozen=True)

    pre_rare: list[Component]
    misid   : 'FitModelConf | None' = None
    # ---------------------
    @classmethod
    def default(cls) -> 'ConstraintsCfg':
        '''
        Returns
        -------------
        Default configuration, mostly needed for tests
        '''
        return cls(pre_rare = [])
    # ---------------------
    @property
    def is_empty(self) -> bool:
        '''
        True if no constraints are present
        '''
        return self.misid is None and self.pre_rare is None
# ------------------------------
# Components
# ------------------------------
class CmbConstraintConf(BaseModel):
    '''
    Class meant to represent configuration for combintorial constraints

    Attributes
    ---------------
    selection : Selection that sample will go through on top of nominal selection, e.g. vetos
    parameters: Parameters that will be constrained
    '''
    component : Component
    trigger   : Trigger
    parameters: list[str]
    selection : dict[Cuts,str]
    fit       : FitConf
    plots     : ZFitPlotterConf
# ------------------------------
class CategoryConf(BaseModel):  # Tested
    '''
    Class meant to configure a fit category
    '''
    selection : dict[Cuts,str]
    model     : ModelFactoryConf
# ------------------------------
# ------------------------------
class ComponentConf(UnpackerModel):         # Tested
    '''
    Class meant to configure the fit for different components

    Attributes
    ------------------
    mass      : Mass used to build PDF, e.g. bp, bp_dtf_jpsi, etc
    norm_range: Range where PDF is normalized to 1
    '''
    model_config = ConfigDict(frozen=True)

    cfg_obs : ObservableConf | None = None
    # ----------------------------------
    @property
    def component_trigger(self) -> Trigger | None:
        '''
        Trigger for current component, if valid, or None
        if it does not exist
        '''
        return getattr(self, 'trigger', None)
    # ---------------------------
    @property
    def obs(self) -> zobs:
        '''
        Returns
        ----------------
        Observable used to build PDF
        '''
        if self.cfg_obs is None:
            raise ValueError('Normalization range was not initialized')

        obs = zfit.Space(
            obs   = 'Mass',
            label = self.cfg_obs.name,
            limits= self.cfg_obs.range)

        return obs
# ------------------------------
class CCbarConf(ComponentConf):         # Tested
    '''
    Class mean to control configuration to fit ccbar components
    '''
    model_config = ConfigDict(frozen=True)

    samples : list[CCbarComponent]
    weights : dict[CCbarWeight,bool]
    fit     : KDEConf
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
            cfg_obs   = cfg_obs,
            samples   = samples,
            weights   = weights,
            fit       = KDEConf.default())
# ------------------------------
class ParametricConf(ComponentConf):  # Tested
    '''
    Class mean to control configuration of fit to parametric models
    '''
    component  : Component
    fit        : FitConf
    categories : dict[str, CategoryConf]
    plots      : ZFitPlotterConf
    # ----------------------
    def filter_category(self, func : Callable) -> Self:
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
                new_name = new_name.replace(old, new)

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
            raise ValueError(f'No category found with name: {name}')

        return self.model_copy(update = {'categories' : new_categories})
# ------------------------------
class NonParametricConf(ComponentConf): # Tested
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

        obs = zfit.Space(
            obs   = 'Mass',
            label = self.cfg_obs.name,
            limits= self.cfg_obs.range)

        return obs
# ------------------------------
class CombinatorialConf(ComponentConf): # Tested
    '''
    Class mean to control configuration of fit to combinatorial
    '''
    model_config = ConfigDict(frozen=True)

    models      : dict[Qsq, ModelFactoryConf ]
    constraints : dict[Qsq, CmbConstraintConf]
# ------------------------------
class MisIDConf(NonParametricConf): # Tested
    '''
    Configuration needed to build MisID components
    '''
    trigger          : Trigger
    project          : Project
    weights          : MisIDSampleWeights
    data_fit         : FitConf
    selection        : dict[Cuts,str]
# ------------------------------
AnyModelConf = CombinatorialConf | ParametricConf | CCbarConf | MisIDConf | NonParametricConf
# ------------------------------
# Fits
# ------------------------------
class FitModelConf(UnpackerModel):
    '''
    Class representing fitting model

    Attributes
    --------------------
    yields   : Contains configurations to build yields for a fitting region/PDF, etc
    selection: Dictionary mapping signal region with selection used to create it
    '''
    model_config = ConfigDict(frozen = True)

    trigger    : Trigger
    selection  : dict[Cuts,str]
    yields     : YieldsConf
    observable : dict[Qsq | MisID, ObservableConf]
    components : dict[Component, AnyModelConf]
    constraints: ConstraintsCfg
    plots      : ZFitPlotterConf
    fit        : FitConf
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
            observable  = {},
            components  = {},
            constraints = ConstraintsCfg.default(),
            plots       = ZFitPlotterConf.default(),
            fit         = FitConf.default())
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
    block   : int             = -1
    nproc   : int             = 1
    log_lvl : int             = 20
    ntoys   : int             = 0
    toy_cfg : ToyConf |  None = None
    # ------------------------
    def _set_cfg_obs(self, cfg : ObservableConf) -> None:
        '''
        Parameters
        --------------
        cfg: Obeservable configuration used for data
        '''
        new_components : dict[Component, AnyModelConf] = {}
        for component, cfg_cmp in self.mod_cfg.components.items():
            new_cfg             = self._update_cfg_obs(cfg_obs = cfg, cfg_cmp = cfg_cmp)
            new_val             = cfg_cmp.model_copy(update = {'cfg_obs' : new_cfg })
            new_components[component] = new_val

        self.mod_cfg = self.mod_cfg.model_copy(update = {'components' : new_components})
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
        if self.mod_cfg.trigger.is_muon:
            return cfg_obs.model_copy(update = {'name' : Mass.b})

        # If fit uses electron non-DTF AND parametric PDF 
        # use unsmeared mass
        if not isinstance(cfg_cmp, (NonParametricConf, CCbarConf)):
            return cfg_obs

        # If fit uses electron non-DTF AND non-parametric PDF
        # use smeared mass
        return cfg_obs.model_copy(update = {'name' : cfg_obs.name.smeared_version })
    # ----------------------
    def model_post_init(self, _):
        '''
        This runs after initialization
        '''
        self._set_logs()
        self._initialize_toy_config()

        cfg_obs = self.mod_cfg.observable[self.q2bin]
        self._set_cfg_obs(cfg = cfg_obs)
    # ----------------------
    def _initialize_toy_config(self) -> None:
        if self.toy_cfg is None:
            return

        update  = {'output' : self.output_directory / 'toys', 'ntoys' : self.ntoys}
        self.toy_cfg.model_copy(update = update)

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
    def cfg_copy(self, replacements : dict[str,str]) -> Self:
        '''
        This method provides a copy of the configuration with the
        categories associated to parametric components, renamed

        Parameters
        -----------------
        replacements: Dictionary where key is the the substring to be replaced
        and value is the replacement

        Returns
        -----------------
        Copy of config with renaming
        '''
        new_components : dict[Component, AnyModelConf] = {}
        for comp, conf in self.mod_cfg.components.items():
            if not isinstance(conf, ParametricConf):
                new_conf = conf.model_copy()
            else:
                new_conf = conf.cfg_copy(replacements = replacements )

            new_components[comp] = new_conf

        new_mod_cfg = self.mod_cfg.model_copy(update = {'components' : new_components})

        return self.model_copy(update = {'mod_cfg' : new_mod_cfg})
    # ----------------------
    def pick_category(self, name : str) -> Self:
        '''
        Parameters
        -----------------
        name: Name of single category, for parametric model to be picked

        Returns
        -----------------
        Copy of config with that category
        '''
        new_components : dict[Component, AnyModelConf] = {}
        for comp, conf in self.mod_cfg.components.items():
            if not isinstance(conf, ParametricConf):
                new_conf = conf.model_copy()
            else:
                new_conf = conf.pick_category(name = name)

            new_components[comp] = new_conf

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

        if self.block == 12:
            return  '(block == 1) || (block == 2)'

        if self.block == 78:
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

        selection.update(self.mod_cfg.selection)

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
    @cached_property
    def output_directory(self) -> Path:
        '''
        Returns
        -----------------
        This function will return the directory WRT which
        the `output_directory` key in the fit config will be defined
        '''
        if not isinstance(self.block, int):
            raise ValueError(f'Block is not an int but {type(self.block)} = {self.block}')

        if self.block == -1:
            block_name = 'all'
        else:
            block_name = f'b{self.block}'

        ana_dir = os.environ.get('ANADIR')
        if ana_dir is None:
            raise RuntimeError('ANADIR variable not set')

        trigger = self.mod_cfg.trigger
        out_dir = Path(ana_dir) / 'fits/data' / self.group / f'{self.fit_name}_{block_name}'
        out_dir = out_dir / self.q2bin.kind / trigger.project / trigger.channel / self.q2bin

        log.debug(f'Using output directory: {out_dir}')

        out_dir.mkdir(parents = True, exist_ok = True)

        return out_dir
    # ----------------------
    @cached_property
    def observable(self) -> zobs:
        '''
        Returns
        -------------
        Zfit observable
        '''
        cfg_obs      = self.mod_cfg.observable[self.q2bin]
        [minx, maxx] = cfg_obs.range
        obs          = zfit.Space(
            obs   = 'Mass',
            label = cfg_obs.name,
            limits= (minx, maxx))

        return obs
# ----------------------
