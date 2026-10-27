'''
Script used to run simultaneous fits for rk, rkst and rx
'''
import argparse

from typing           import Final
from pydantic         import BaseModel
from pathlib          import Path
from contextlib       import ExitStack
from dmu.generic      import UnpackerModel, utilities as gut
from dmu.generic      import Serializable
from dmu.stats        import ParameterLibrary as PL
from dmu.stats        import utilities as sut
from dmu.stats        import ConstraintAdder
from dmu.stats        import Constraints
from dmu.stats        import FitResult
from dmu.workflow     import Cache
from dmu              import LogStore, LogLevels
from rx_selection     import selection as sel
from rx_common        import Brem, Component, Region
from rx_common        import MVAWp, Qsq

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
    Config holding all the information needed in current script
    '''
    cfgs : dict[Region,RXFitConfig]
    '''Dictionary mapping fitting region and corresponding configuration'''
    syst : Systematic
    '''Systematic variation used for fit'''
    q2bin: Qsq
    '''q2 bin for which fit is done'''
    dry_run: bool
    '''If true will not fit data, but will build NLL'''
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
def _parse_args() -> Conf:
    '''
    Returns
    --------------
    Instance of configuration class, built from arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to fit RX data')
    parser.add_argument('-b', '--block'  , type=int           , help='Block number, if not passed will do all data'    , choices =[-1,1,2,3,4,5,6,7,8], default=-1)
    parser.add_argument('-g', '--group'  , type=str           , help='Name of group to which fit belongs, e.g. toys'   , required= True)
    parser.add_argument('-k', '--kind'   , type=SimFit        , help='Type of simultaneous fit'                        , required= True)
    parser.add_argument('-n', '--ncores' , type=int           , help='Number of processes'                             , default =1)
    parser.add_argument('-l', '--log_lvl', type=LogLevels     , help='Logging level'                                   , default =20)
    parser.add_argument('-q', '--q2bin'  , type=Qsq           , help='q2 bin'       , choices=Qsq.rare                 , required=True)
    parser.add_argument('-s', '--syst'   , type=Systematic    , help='Systematic variation used for this fit'          , default = Systematic.nominal, choices=Systematic)
    parser.add_argument('-C', '--mva_cmb', type=MVAWp.from_str, help='MVA working point, e.g. 0200; 0100-0300'         , default = MVAWp.none())
    parser.add_argument('-P', '--mva_prc', type=MVAWp.from_str, help='MVA working point, e.g. 0200; 0100-0300'         , default = MVAWp.none())
    parser.add_argument('-d', '--dry_run', action='store_true', help='If used, will not fit the data')
    args = parser.parse_args()

    regions : list[Region] = args.kind.regions

    cfgs = { region : _cfg_from_args(region = region, args = args) for region in regions }

    cfg  = Conf(
        cfgs   = cfgs, 
        syst   = args.syst, 
        q2bin  = args.q2bin, 
        dry_run= args.dry_run)

    return cfg
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
def _cfg_from_args(
    region : Region,
    args   : argparse.Namespace) -> RXFitConfig:
    '''
    Parameters
    -------------
    region: Signal region
    args  : Object storing configuration

    Returns
    -------------
    Object storing full fit configuration
    '''
    data_mod= gut.load_data(
        package= 'fitter_data',
        fpath  = f'rare/{region.trigger.project}/{region.trigger.channel}/data.yaml')

    config_replacements = _get_replacements(kind = args.kind, syst = args.syst)
    with UnpackerModel.replacements(files = config_replacements):
        mod_cfg = FitModelConf(**data_mod)

    if mod_cfg.trigger.is_electron:
        name = 'brem_x12'
    else:
        name = 'brem_xx0'

    cfg = RXFitConfig(
        name    = name,
        mod_cfg = mod_cfg,
        group   = f'{args.group}/{args.syst}',
        block   = args.block,
        q2bin   = args.q2bin,
        ncores  = args.ncores,
        mva_cmb = args.mva_cmb,
        mva_prc = args.mva_prc,
        log_lvl = args.log_lvl)

    return cfg
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
            nll         = cfg_nll.nll,
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

    _save_results(
        nlls = d_nll,
        res  = res,
        cfg  = cfg)
# ----------------------
def _get_conf() -> Conf:
    '''
    Returns dictionary mapping signal region to configuration in region
    '''
    ctx_1 = UnpackerModel.package(name = 'fitter_data')
    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        cfgs = _parse_args()

    return cfgs
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg = _get_conf()
    _set_logs()

    cfg.to_json(path = cfg.out_dir / cfg.q2bin / 'config.json')

    ctx_1 = DataPreprocessor.use_database()
    ctx_2 = ConstraintAdder.fixed_parameters(value = False)
    ctx_3 = sut.root_directory(root_dir=cfg.out_dir / 'failed_nll')
    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)

        _fit(cfg=cfg)
# ----------------------
if __name__ == '__main__':
    main()
