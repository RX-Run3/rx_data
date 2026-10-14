'''
Script used to interact with DataFitter tool
and run fits to the resonant mode
'''

import os
import argparse

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from typing        import Final
from ROOT          import EnableImplicitMT # type: ignore
from contextlib    import ExitStack
from dmu           import LogStore
from dmu.stats     import GofCalculator
from dmu.workflow  import Cache
from dmu.stats     import ParameterLibrary as PL
from dmu.stats     import utilities as sut 
from dmu.generic   import utilities as gut
from dmu.generic   import UnpackerModel

from fitter        import DataPreprocessor
from fitter        import add_constraints 
from fitter        import NLLConf
from rx_common     import MVAWp
from fitter        import FitModelConf
from fitter        import ToyConf
from fitter        import RXFitConfig
from fitter        import DataFitter
from fitter        import LikelihoodFactory
from rx_selection  import selection as sel
from rx_common     import AlternativeProject, Brem, Qsq, Component, Region

log=LogStore.add_logger('fitter:fit_rx_reso')
_DATA        : Final[Component ]                 = Component.data_24
_ALT_PROJECT : Final[AlternativeProject | None ] = None # AlternativeProject.bad_ecal 
# ----------------------
def _set_logs() -> None:
    '''
    Hides log messages from certain tools
    '''
    LogStore.set_level('rx_fitter:inclusive_sample_weights', 30)
    LogStore.set_level('rx_fitter:inclusive_decays_weights', 30)

    LogStore.set_level('rx_data:path_splitter'    , 30)
    LogStore.set_level('rx_data:spec_maker'       , 30)
    LogStore.set_level('rx_data:sample_patcher'   , 30)
    LogStore.set_level('rx_data:sample_emulator'  , 30)
    LogStore.set_level('rx_data:rdf_getter'       , 30)

    LogStore.set_level('fitter:base_fitter'       , 30)
    LogStore.set_level('fitter:sim_fitter'        , 30)
    LogStore.set_level('fitter:likelihood_factory', 30)
# ----------------------
def _get_wp(val : str) -> MVAWp:
    '''
    Parameters
    ------------
    val: Float representing working point

    Returns
    ------------
    MVA wp instance
    '''
    return MVAWp(float(val))
# ----------------------
def _parse_args() -> RXFitConfig:
    '''
    Returns
    --------------
    Instance of configuration class, built from arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to fit RX data')
    parser.add_argument('-b', '--block'  , type=int    , help='Block number, if not passed will do all data'    , choices =[1,2,3,4,5,6,7,8], default=-1)
    parser.add_argument('-g', '--group'  , type=str    , help='Group to which fits belong, e.g. reso_no_dtf'    , required=True)
    parser.add_argument('-c', '--fit_cfg', type=str    , help='Name of configuration, e.g. reso/rkst/ee'        , required=True)
    parser.add_argument('-t', '--toy_cfg', type=str    , help='Name of toy config, e.g. toys/maker.yaml'        , default ='')
    parser.add_argument('-n', '--ncores' , type=int    , help='Number of cores to process dataframes'           , default =1)
    parser.add_argument('-N', '--ntoys'  , type=int    , help='If specified, this will override ntoys in config', default =0)
    parser.add_argument('-l', '--log_lvl', type=int    , help='Logging level', choices=[5, 10, 20, 30]          , default =20)
    parser.add_argument('-q', '--q2bin'  , type=Qsq    , help='q2 bin'      , choices=Qsq                       , required=True)
    parser.add_argument('-r', '--rawmass',               help='If used, will fit with non-DTF mass'             , action  ='store_true') 
    parser.add_argument('-C', '--mva_cmb', type=_get_wp, help='Cut on combinatorial MVA working point'          , required=True)
    parser.add_argument('-P', '--mva_prc', type=_get_wp, help='Cut on part reco MVA working point'              , required=True)
    args = parser.parse_args()

    if args.rawmass:
        conf_name = 'data_no_dtf.yaml'
    else:
        conf_name = 'data.yaml'

    log.info(f'Using {conf_name} config')
    data = gut.load_data(
        package='fitter_data',
        fpath  =f'{args.fit_cfg}/{conf_name}')
    fit_cfg = FitModelConf(**data)

    if args.toy_cfg:
        data = gut.load_data(
            package='fitter_data',
            fpath=args.toy_cfg)

        toy_cfg = ToyConf(**data)
    else:
        toy_cfg = None

    if fit_cfg.trigger.is_electron:
        name = 'brem_x12'
    else:
        name = 'brem_xx0'

    cfg         = RXFitConfig(
        mod_cfg = fit_cfg,
        toy_cfg = toy_cfg,
        name    = name,
        ncores  = args.ncores,
        group   = args.group,
        block   = args.block,
        q2bin   = args.q2bin,
        mva_cmb = args.mva_cmb,
        mva_prc = args.mva_prc,
        log_lvl = args.log_lvl,
        ntoys   = args.ntoys)

    return cfg
# ----------------------
def _get_brem_nll(
    brem : Brem,
    cfg  : RXFitConfig) -> NLLConf:
    '''
    Parameters
    -------------
    cfg : Fit configuration
    brem: Bremsstrahlung category for current fit

    Returns
    -------------
    Object holding NLL
    '''
    project = cfg.mod_cfg.trigger.project.alternative(key = _ALT_PROJECT)

    ftr = LikelihoodFactory(
        name   = cfg.name,
        obs    = cfg.obs,
        q2bin  = cfg.q2bin,
        sample = _DATA,
        cfg    = cfg.mod_cfg)
    cfg_nll = ftr.run(project = project)

    nll, cons = add_constraints(
        brem  = brem,
        nll   = cfg_nll.nll,
        cfg   = cfg)

    return cfg_nll.model_copy(update = {'nll' : nll, 'constraints' : cons})
# ----------------------
def _get_region_nll(brem : Brem, cfg : RXFitConfig) -> NLLConf:
    '''
    Parameters
    -------------
    region: Brem region
    cfg   : Full configuration

    Returns
    -------------
    NLL for fitting brem category for a specific block
    '''
    cfg = cfg.pick_category(
        q2bin= cfg.q2bin,
        name = str(brem))

    with sel.update_selection(d_sel = brem.selection):
        replacements = {'BLOCK' : f'b{cfg.block}'}
        cfg.name     = str(brem)
        cfg          = cfg.cfg_copy(
            q2bin        = cfg.q2bin,
            replacements = replacements)

        return _get_brem_nll(cfg=cfg, brem = brem)
# ----------------------
def _fit_electron(cfg : RXFitConfig) -> dict[Region, NLLConf]:
    '''
    Parameters
    -------------
    cfg: Full config controlling fit

    Returns
    -------------
    Dictionary with fitting region mapped to NLLConf
    '''
    br_1 = Region(brem = Brem.one, trigger = cfg.mod_cfg.trigger)
    br_2 = Region(brem = Brem.two, trigger = cfg.mod_cfg.trigger)

    d_nll : dict[Region,NLLConf] = {}

    d_nll[br_1] = _get_region_nll(brem = Brem.one, cfg = cfg)
    d_nll[br_2] = _get_region_nll(brem = Brem.two, cfg = cfg)

    with GofCalculator.disabled(value=True):
        ftr = DataFitter(
            q2bin = cfg.q2bin,
            d_nll = d_nll,
            cfg   = cfg.mod_cfg)
        res = ftr.run(skip_fit = False)

    log.info(res)

    return d_nll
# ----------------------
def _fit_muon(cfg : RXFitConfig) -> dict[Region,NLLConf]:
    '''
    Parameters
    -------------
    cfg: Full config controlling fit

    Returns
    -------------
    Dictionary with fitting region mapped to NLLConf
    '''
    d_nll : dict[Region,NLLConf] = {}

    region   = Region(brem = Brem.zero, trigger = cfg.mod_cfg.trigger)
    cfg.name = region.name 
    d_nll[region] = _get_brem_nll(cfg=cfg, brem = Brem.zero)

    with GofCalculator.disabled(value=True):
        ftr = DataFitter(
            q2bin= cfg.q2bin,
            d_nll= d_nll,
            cfg  = cfg.mod_cfg)
        res = ftr.run(skip_fit=False)

    log.info(res)

    return d_nll
# ----------------------
def main():
    '''
    Entry point
    '''
    _set_logs()

    with UnpackerModel.package(name = 'fitter_data'):
        cfg = _parse_args()

    if cfg.ncores > 1:
        EnableImplicitMT(cfg.ncores)
        log.info(f'Using {cfg.ncores} cores')

    ctx_1 = Cache.cache_root(path=cfg.output_directory)
    ctx_2 = PL.parameter_schema(cfg=cfg.mod_cfg.yields)
    ctx_3 = sel.custom_selection(d_sel=cfg.overriding_selection)
    ctx_4 = DataPreprocessor.use_database()

    with ExitStack() as stack:
        stack.enter_context(ctx_1)
        stack.enter_context(ctx_2)
        stack.enter_context(ctx_3)
        stack.enter_context(ctx_4)

        if cfg.is_electron:
            d_nll = _fit_electron(cfg=cfg)
        else:
            d_nll = _fit_muon(cfg=cfg)

    for region, nll_cfg in d_nll.items():
        out_path = cfg.fit_directory / region.name / 'nll.bytes'
        log.info(f'Saving: {out_path}')
        sut.save_nll(loss = nll_cfg.nll, path = out_path)
# ----------------------
if __name__ == '__main__':
    main()
