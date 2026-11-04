'''
Script used to run simultaneous fits for rk, rkst and rx
'''
import tyro

from typing           import Final, Annotated
from pydantic         import BaseModel, computed_field
from pathlib          import Path
from contextlib       import ExitStack
from functools        import cached_property
from dmu.generic      import UnpackerModel, utilities as gut
from dmu.generic      import Serializable
from dmu.stats        import ParameterLibrary as PL
from dmu.stats        import utilities as sut
from dmu.stats        import ConstraintAdder
from dmu.stats        import Constraints, ConstraintMode
from dmu.stats        import FitResult
from dmu.workflow     import Cache
from dmu              import LogStore, LogLevels
from rx_selection     import selection as sel
from rx_common        import Brem, Component, Region
from rx_common        import MVAWp, Qsq, QsqDef

from fitter           import DataPreprocessor
from fitter           import RXFitConfig
from fitter           import add_constraints
from fitter           import DataFitterSim
from fitter           import LikelihoodFactory
from fitter           import FitModelConf
from fitter           import NLLConf
from fitter           import SimFit
from fitter           import ModelSystematics
from fitter           import Systematic

log=LogStore.add_logger('fitter:fit_rx_rare_sim')

_DATA_SAMPLE : Final[Component] = Component.data_24
# ----------------------
class Conf(BaseModel, Serializable, frozen=True):
    '''
    Script used to run simultaneous fits for RX, RK or RKst
    '''
    cmode  : Annotated[ConstraintMode, tyro.conf.arg(aliases=['-c'])] = ConstraintMode.apply
    '''Controls how to use constraints'''
    syst   : Annotated[Systematic, tyro.conf.arg(aliases=['-s'])]
    '''Systematic variation used for fit'''
    q2bin  : Annotated[Qsq        , tyro.conf.arg(aliases=['-q'])]
    '''q2 bin for which fit is done'''
    q2def  : Annotated[QsqDef     , tyro.conf.arg(aliases=['-Q'])] = QsqDef.default
    '''Describes how the q2 was calculated, e.g. with track information only'''
    dry_run: Annotated[bool       , tyro.conf.arg(aliases=['-d'])] = False
    '''If true will not fit data, but will build NLL'''
    block  : Annotated[int        , tyro.conf.arg(aliases=['-b'])] = -1
    '''Block number, if not passed will do all data'''
    group  : Annotated[str        , tyro.conf.arg(aliases=['-g'])] = ''
    '''Name of group to which fit belongs, used for naming output directory'''
    kind   : Annotated[SimFit     , tyro.conf.arg(aliases=['-k'])] = SimFit.rx
    '''Type of simultaneous fit'''
    ncores : Annotated[int        , tyro.conf.arg(aliases=['-n'])] = 1
    '''Number of cores'''
    log_lvl: Annotated[LogLevels  , tyro.conf.arg(aliases=['-l'])] = LogLevels.info
    '''Logging level'''
    mva_cmb: Annotated[MVAWp      , tyro.conf.arg(aliases=['-C'], constructor=MVAWp.from_str)] = MVAWp.none()
    '''Combinatorial MVA working point, if used will override default, e.g. 0.8'''
    mva_prc: Annotated[MVAWp      , tyro.conf.arg(aliases=['-P'], constructor=MVAWp.from_str)] = MVAWp.none()
    '''Part reco MVA working point, if used will override default, e.g. 0.8'''
    # ---------------------------
    @computed_field
    @cached_property
    def cfgs(self) -> dict[Region, RXFitConfig]:
        '''
        Returns dictionary mapping fitting region to
        corresponding fitting configuration
        '''
        ctx_1 = UnpackerModel.package(name = 'fitter_data')
        with ExitStack() as stack:
            stack.enter_context(ctx_1)
            cfgs = { region : self._cfg_from_args(region = region) for region in self.kind.regions }

        return cfgs
    # ---------------------------
    def _cfg_from_args(self, region : Region) -> RXFitConfig:
        '''
        Parameters
        -------------
        region: Signal region

        Returns
        -------------
        Object storing full fit configuration
        '''
        data_mod= gut.load_data(
            package= 'fitter_data',
            fpath  = f'rare/{region.trigger.project}/{region.trigger.channel}/data.yaml')

        config_replacements = _get_replacements(kind = self.kind, syst = self.syst)
        with UnpackerModel.replacements(files = config_replacements):
            mod_cfg = FitModelConf(**data_mod)

        if mod_cfg.trigger.is_electron:
            name = 'brem_x12'
        else:
            name = 'brem_xx0'

        group   = self._get_group_string()

        fit_cfg = RXFitConfig(
            name    = name,
            mod_cfg = mod_cfg,
            group   = group,
            block   = self.block,
            q2bin   = self.q2bin,
            ncores  = self.ncores,
            mva_cmb = self.mva_cmb,
            mva_prc = self.mva_prc,
            log_lvl = self.log_lvl)

        return fit_cfg
    # ---------------------------
    @property
    def out_dir(self) -> Path:
        '''
        Path to directory containing rk and rkst directories
        '''
        s_path : set[Path] = set()
        for cfg in self.cfgs.values():
            path = cfg.output_directory.parent.parent.parent
            s_path.add(path)

        if len(s_path) != 1:
            raise ValueError(f'Not found one and only one output directory: {s_path}')

        return list(s_path)[0]
    # ----------------------
    def _get_group_string(self) -> str:
        '''
        Returns {group_name}/{systematic} part of the output path
        '''
        parts : list[str] = [self.group]
        if self.q2def != QsqDef.default:
            parts.append(f'qsq_{self.q2def}')

        if self.cmode != ConstraintMode.apply:
            parts.append(f'cns_{self.cmode}')

        group = '-'.join(parts)

        return f'{group}/{self.syst}'
# ----------------------
def _set_logs() -> None:
    '''
    Silence loggers
    '''
    LEVEL=30

    LogStore.set_level('rx_data:db_maker'        , LEVEL)
    LogStore.set_level('rx_data:path_splitter'   , LEVEL)
    LogStore.set_level('rx_data:data_model'      , LEVEL)
    LogStore.set_level('rx_data:rdf_getter'      , LEVEL)
    LogStore.set_level('rx_data:spec_maker'      , LEVEL)
    LogStore.set_level('rx_data:sample_patcher'  , LEVEL)
    LogStore.set_level('rx_data:sample_emulator' , LEVEL)
    LogStore.set_level('rx_selection:selection'  , LEVEL)
    LogStore.set_level('rx_selection:registry'   , LEVEL)

    LogStore.set_level('rx_efficiencies:acceptance_reader', LEVEL)

    LogStore.set_level('dmu:workflow:cache'      , LEVEL)
    LogStore.set_level('dmu:stats:utilities'     , LEVEL)
    LogStore.set_level('dmu:stats:model_factory' , LEVEL)
    LogStore.set_level('dmu:stats:fitter'        , LEVEL)
    LogStore.set_level('dmu:stats:minimizers'    , LEVEL)
    LogStore.set_level('dmu:pdataframe:utilities', LEVEL)
    LogStore.set_level('dmu:stats:fit_result'    , LEVEL)

    LogStore.set_level('fitter:base_fitter'      , LEVEL)

    LogStore.set_level('fitter:sim_fitter'       , 20)
    LogStore.set_level('fitter:data_preprocessor', 20)
# ----------------------
def _get_replacements(kind : SimFit, syst : Systematic) -> dict[str,str]:
    '''
    Parameters
    ------------------
    kind: Symbolizes measurement been made

    Returns
    ------------------
    Replacements needed for config files describing yields.
    Needed in order to reparametrize in function of rk, rkst or both
    '''
    match kind:
        case SimFit.rk:
            repl = {'rk/rare_muon.yaml' : 'rk/rare_muon_simultaneous.yaml'}
        case SimFit.rkst:
            repl = {'rkst/rare_muon.yaml' : 'rkst/rare_muon_simultaneous.yaml'}
        case SimFit.rx:
            repl = {
                'rk/rare_electron.yaml' : 'rk/rare_electron_simultaneous.yaml', # nkstee -> nkee * eff_ratio
                'rk/rare_muon.yaml'     : 'rk/rare_muon_simultaneous.yaml',     # nmumu  -> rk   * nee / ck
                'rkst/rare_muon.yaml'   : 'rkst/rare_muon_simultaneous.yaml'}   # nmumu  -> rkst * nee / ck*

    msys = ModelSystematics.load()
    replacements = msys.get(syst = syst)
    replacements.update(repl)

    return replacements
# ----------------------
def _get_region_nll(brem : Brem, cfg : RXFitConfig) -> NLLConf:
    ctx_1 = Cache.cache_root(path=cfg.output_directory)
    ctx_2 = PL.parameter_schema(cfg=cfg.mod_cfg.yields)
    ctx_3 = sel.custom_selection(d_sel=cfg.overriding_selection)
    ctx_4 = sut.root_directory(root_dir=cfg.output_directory / 'failed_nll')
    ctx_5 = sel.update_selection(d_sel = brem.selection)

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)
        stack.enter_context(ctx_4)
        stack.enter_context(ctx_5)

        ftr = LikelihoodFactory(
            name   = str(brem),
            obs    = cfg.obs,
            q2bin  = cfg.q2bin,
            sample = _DATA_SAMPLE,
            cfg    = cfg.mod_cfg)
        cfg_nll  = ftr.run()

        nll, cons = add_constraints(
            brem  = brem,
            nll   = cfg_nll.nll,
            cfg   = cfg)

        return NLLConf(
            nll         = nll,
            selection   = cfg_nll.selection,
            constraints = cons.to_list())
# ----------------------
def _get_nll(
    brem: Brem,
    cfg : RXFitConfig) -> NLLConf:
    '''
    Parameters
    -----------------
    brem: Brem category
    cfg : Configuration for fit

    Returns
    -----------------
    Dictionary mapping signal region with NLL container
    '''
    if brem.is_composite:
        # Put all the elementary regions in same config
        cfg_brem         = cfg.cfg_clone(
            prefix       = 'BREM',
            q2bin        = cfg.q2bin,
            brems        = [ brem for brem in brem.components ])
    else:
        # Pick only elementary region
        cfg_brem         = cfg.cfg_copy(
            q2bin        = cfg.q2bin,
            replacements = {'BREM' : str(brem)})

    return _get_region_nll(brem = brem, cfg = cfg_brem)
# ----------------------
def _save_results(
    nlls : dict[Region,NLLConf],
    res  : FitResult,
    cfg  : Conf) -> None:
    '''
    Parameters
    ----------------
    nlls: Dictionary mapping region with likelihood holder
    res : Fit result
    cfg : Object holding configuration
    '''
    _nlls = [ nll_cfg.nll    for nll_cfg in nlls.values() ]
    _cnss = { cns.name : cns for nll_cfg in nlls.values() for cns in nll_cfg.constraints }

    nll   = gut.add_container(elements = _nlls)
    cns   = Constraints(root = _cnss)

    dir_path = cfg.out_dir / f'{cfg.q2bin}'

    sut.save_nll(loss = nll, path = dir_path / 'nll.bytes')
    cns.to_json(path = dir_path / 'constraints.json')
    res.to_json(path = dir_path / 'result.json')
# ----------------------
def _fit(cfg : Conf) -> None:
    '''
    This is where DataFitter is used
    '''
    d_nll : dict[Region, NLLConf] = {}
    for region, region_cfg in cfg.cfgs.items():
        d_nll[region] = _get_nll(cfg = region_cfg, brem = region.brem)

    if cfg.dry_run:
        log.info('Skipping fit to data, dry run')
        return

    log.info(30 * '-')
    log.info('Fitting data')
    log.info(30 * '-')

    ftr = DataFitterSim(
        d_nll = d_nll,
        q2bin = cfg.q2bin,
        d_cfg = cfg.cfgs)
    res = ftr.run(skip_fit = False)

    if res is None:
        return

    _save_results(
        nlls = d_nll,
        res  = res,
        cfg  = cfg)
# ----------------------
def main():
    '''
    Entry point
    '''
    _set_logs()

    cfg = tyro.cli(Conf)
    cfg.to_json(path = cfg.out_dir / cfg.q2bin / 'config.json')

    ctx_1 = DataPreprocessor.use_database()
    ctx_2 = ConstraintAdder.mode(value = cfg.cmode)
    ctx_3 = sut.root_directory(root_dir=cfg.out_dir / 'failed_nll')
    ctx_4 = sel.override_qsq(kind = cfg.q2def)
    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)
        stack.enter_context(ctx_4)

        _fit(cfg=cfg)
# ----------------------
if __name__ == '__main__':
    main()
