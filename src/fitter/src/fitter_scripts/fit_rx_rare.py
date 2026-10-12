'''
Script used to interact with DataFitter tool
and run fits
'''
import argparse
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from ROOT             import EnableImplicitMT # type: ignore
from typing           import Final
from contextlib       import ExitStack
from dmu.generic      import UnpackerModel, utilities as gut
from dmu.stats        import ParameterLibrary as PL
from dmu.stats        import utilities as sut
from dmu.stats        import ConstraintAdder
from dmu.workflow     import Cache
from dmu              import LogStore
from rx_selection     import selection as sel
from rx_common        import Brem, Component, Region
from rx_common        import MVAWp

from fitter           import DataPreprocessor
from fitter           import RXFitConfig
from fitter           import add_constraints 
from fitter           import DataFitter
from fitter           import LikelihoodFactory
from fitter           import FitModelConf
from fitter           import ToyConf
from fitter           import NLLConf

log=LogStore.add_logger('fitter:fit_rx_rare')

_DATA_SAMPLE : Final[Component] = Component.data_24
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
def _parse_args() -> RXFitConfig:
    '''
    Returns
    --------------
    Instance of configuration class, built from arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to fit RX data')
    parser.add_argument('-b', '--block'  , type=int           , help='Block number, if not passed will do all data'    , choices =[-1,1,2,3,4,5,6,7,8], default=-1)
    parser.add_argument('-g', '--group'  , type=str           , help='Name of group to which fit belongs, e.g. toys'   , required= True)
    parser.add_argument('-c', '--fit_cfg', type=str           , help='Name of configuration, e.g. rare/rk/ee'          , required= True)
    parser.add_argument('-t', '--toy_cfg', type=str           , help='Name of toy config, e.g. toys/maker.yaml'        , default =   '')
    parser.add_argument('-N', '--ntoys'  , type=int           , help='If specified, this will override ntoys in config', default =0)
    parser.add_argument('-n', '--ncores' , type=int           , help='Number of processes'                             , default =1)
    parser.add_argument('-l', '--log_lvl', type=int           , help='Logging level', choices=[5, 10, 20, 30]          , default =20)
    parser.add_argument('-q', '--q2bin'  , type=str           , help='q2 bin'      , choices=['low', 'central', 'high'], required=True)
    parser.add_argument('-C', '--mva_cmb', type=MVAWp.from_str, help='MVA working point, e.g. 0200; 0100-0300'         , required=True)
    parser.add_argument('-P', '--mva_prc', type=MVAWp.from_str, help='MVA working point, e.g. 0200; 0100-0300'         , required=True)
    args = parser.parse_args()

    return _cfg_from_args(args = args)
# ----------------------
def _cfg_from_args(args : argparse.Namespace) -> RXFitConfig:
    '''
    Parameters
    -------------
    args: Object storing configuration

    Returns
    -------------
    Object storing full fit configuration
    '''
    data_mod= gut.load_data(package='fitter_data', fpath=f'{args.fit_cfg}/data.yaml')
    mod_cfg = FitModelConf(**data_mod)

    data_toy= gut.load_data(package='fitter_data', fpath=args.toy_cfg) if args.toy_cfg else None
    toy_cfg = ToyConf(**data_toy) if data_toy else None

    if mod_cfg.trigger.is_electron:
        name = 'brem_x12'
    else:
        name = 'brem_xx0'

    cfg = RXFitConfig(
        name    = name,
        mod_cfg = mod_cfg,
        toy_cfg = toy_cfg,
        group   = args.group,
        block   = args.block,
        q2bin   = args.q2bin,
        ncores  = args.ncores,
        mva_cmb = args.mva_cmb,
        mva_prc = args.mva_prc,
        log_lvl = args.log_lvl,
        ntoys   = args.ntoys)

    return cfg
# ----------------------
def _get_region_nll(brem : Brem, cfg : RXFitConfig) -> NLLConf:
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

    return cfg_nll.model_copy(update = {'nll' : nll, 'constraints' : cons})
# ----------------------
def _get_nll(
    brems: list[Brem],
    cfg  : RXFitConfig) -> dict[Region,NLLConf]:
    '''
    Parameters
    -----------------
    brems: List of brem categories
    cfg  : Configuration for fit

    Returns
    -----------------
    Dictionary mapping signal region with NLL container
    '''
    d_nll : dict[Region,NLLConf] = {}
    for brem in brems:
        if brem.is_composite:
            # Put all the elementary regions in same config
            cfg_brem         = cfg.cfg_clone(
                prefix       = 'BREM', 
                q2bin        = cfg.q2bin,
                regions      = [ elm.region for elm in brem.components ])
        else:
            # Pick only elementary region 
            cfg_brem         = cfg.cfg_copy(
                q2bin        = cfg.q2bin,
                replacements = {'BREM' : str(brem)})

        with sel.update_selection(d_sel = brem.selection):
            d_nll[brem.region] = _get_region_nll(brem = brem, cfg = cfg_brem)

    return d_nll
# ----------------------
def _fit(cfg : RXFitConfig) -> None:
    '''
    This is where DataFitter is used
    '''
    #brems = [Brem.one, Brem.two]
    brems = [Brem.brx12]

    d_nll = _get_nll(cfg = cfg, brems = brems)
    ftr   = DataFitter(
        q2bin = cfg.q2bin,
        d_nll = d_nll,
        cfg   = cfg.mod_cfg)
    ftr.run(skip_fit = False)
# ----------------------
def main():
    '''
    Entry point
    '''
    with UnpackerModel.package(name = 'fitter_data'):
        cfg = _parse_args()

    if cfg.ncores > 1:
        log.info(f'Running with {cfg.ncores} cores')
        EnableImplicitMT(cfg.ncores)

    _set_logs()

    ctx_1 = Cache.cache_root(path=cfg.output_directory)
    ctx_2 = PL.parameter_schema(cfg=cfg.mod_cfg.yields)
    ctx_3 = sel.custom_selection(d_sel=cfg.overriding_selection)
    ctx_4 = sut.root_directory(root_dir=cfg.output_directory / 'failed_nll')
    ctx_5 = DataPreprocessor.use_database()
    ctx_6 = ConstraintAdder.fixed_parameters(value = False)

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)
        stack.enter_context(ctx_4)
        stack.enter_context(ctx_5)
        stack.enter_context(ctx_6)

        _fit(cfg=cfg)
# ----------------------
if __name__ == '__main__':
    main()
