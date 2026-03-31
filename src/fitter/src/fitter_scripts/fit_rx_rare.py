'''
Script used to interact with DataFitter tool
and run fits
'''
import argparse
import os

os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from dask.distributed import Client, LocalCluster
from typing        import Final
from contextlib    import ExitStack
from omegaconf     import DictConfig
from dmu.stats     import ParameterLibrary as PL
from dmu.generic   import UnpackerModel, utilities as gut
from dmu.stats     import ConstraintAdder
from dmu.stats     import Constraint
from dmu.workflow  import Cache
from dmu           import LogStore
from zfit.loss     import ExtendedUnbinnedNLL
from rx_data       import RDFLoader
from rx_selection  import selection as sel
from rx_common     import Component

from fitter        import RXFitConfig
from fitter        import ConstraintReader
from fitter        import DataFitter
from fitter        import LikelihoodFactory
from fitter        import ToyMaker
from fitter        import FitModelConf
from fitter        import ToyConf
from fitter        import MVAWp

log=LogStore.add_logger('fitter:fit_rx_rare')

DATA_SAMPLE : Final[Component] = Component.data_24 
# ----------------------
def _set_logs() -> None:
    '''
    Silence loggers
    '''
    LEVEL=30

    LogStore.set_level('rx_data:path_splitter'   , LEVEL)
    LogStore.set_level('rx_data:data_model'      , LEVEL)
    LogStore.set_level('rx_data:rdf_getter'      , LEVEL)
    LogStore.set_level('rx_data:spec_maker'      , LEVEL)
    LogStore.set_level('rx_data:sample_patcher'  , LEVEL)
    LogStore.set_level('rx_data:sample_emulator' , LEVEL)
    LogStore.set_level('rx_selection:selection'  , LEVEL)

    LogStore.set_level('dmu:workflow:cache'      , LEVEL)
    LogStore.set_level('dmu:stats:utilities'     , LEVEL)
    LogStore.set_level('dmu:stats:model_factory' , LEVEL)
    LogStore.set_level('dmu:stats:fitter'        , LEVEL)
    LogStore.set_level('dmu:stats:minimizers'    , LEVEL)

    LogStore.set_level('fitter:data_preprocessor', LEVEL)
    LogStore.set_level('fitter:base_fitter'      , LEVEL)
# ----------------------
def _get_client(cfg : RXFitConfig) -> Client | None:
    '''
    Parameters
    -------------
    cfg: Configuration object

    Returns
    -------------
    Client if using multiple processes, or None
    '''
    if cfg.nproc == 1:
        return None

    cluster = LocalCluster(
       n_workers         =cfg.nproc, 
       threads_per_worker=1, 
       processes         =True, 
       memory_limit      ='4GiB')

    return Client(cluster)
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
def _parse_args(args : DictConfig | argparse.Namespace | None = None) -> RXFitConfig:
    '''
    Returns
    --------------
    Instance of configuration class, built from arguments
    '''
    if args is None:
        parser = argparse.ArgumentParser(description='Script used to fit RX data')
        parser.add_argument('-b', '--block'  , type=int    , help='Block number, if not passed will do all data'    , choices =[-1,1,2,3,4,5,6,7,8], default=-1)
        parser.add_argument('-g', '--group'  , type=str    , help='Name of group to which fit belongs, e.g. toys'   , required= True)
        parser.add_argument('-c', '--fit_cfg', type=str    , help='Name of configuration, e.g. rare/rk/ee'          , required= True)
        parser.add_argument('-t', '--toy_cfg', type=str    , help='Name of toy config, e.g. toys/maker.yaml'        , default =   '')
        parser.add_argument('-N', '--ntoys'  , type=int    , help='If specified, this will override ntoys in config', default =0)
        parser.add_argument('-n', '--nproc'  , type=int    , help='Number of processes'                             , default =1)
        parser.add_argument('-l', '--log_lvl', type=int    , help='Logging level', choices=[5, 10, 20, 30]          , default =20)
        parser.add_argument('-q', '--q2bin'  , type=str    , help='q2 bin'      , choices=['low', 'central', 'high'], required=True)
        parser.add_argument('-C', '--mva_cmb', type=_get_wp, help='MVA working point, e.g. 0.2; 0.1 0.3'            , required=True)
        parser.add_argument('-P', '--mva_prc', type=_get_wp, help='MVA working point, e.g. 0.2; 0.1 0.3'            , required=True)
        args = parser.parse_args()

    return _cfg_from_args(args = args)
# ----------------------
def _cfg_from_args(args : DictConfig | argparse.Namespace) -> RXFitConfig:
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
        nproc   = args.nproc,
        mva_cmb = args.mva_cmb,
        mva_prc = args.mva_prc,
        log_lvl = args.log_lvl,
        ntoys   = args.ntoys)

    return cfg
# ----------------------
def _add_constraints(
    nll : ExtendedUnbinnedNLL,
    cfg : RXFitConfig) -> tuple[ExtendedUnbinnedNLL, list[Constraint]]:
    '''
    Parameters
    -------------
    nll: Likelihood
    cfg: Object holding configuration for fit 

    Returns
    -------------
    Tuple with:

    - Constrained likelihood
    - List of constraints
    '''
    signal = cfg.mod_cfg.trigger.get_signal_component(qsq = cfg.q2bin)
    crd  = ConstraintReader(
        signal = signal,
        nll    = nll, 
        cfg    = cfg)
    cons = crd.get_constraints(save_to = cfg.output_directory / 'constraints/all.yaml')

    if not cons:
        log.warning('Not using any constraints')

    log.info('Constraints:')
    for constraint in cons:
        log.info(constraint)

    cad  = ConstraintAdder(nll=nll, constraints=cons)
    nll  = cad.get_nll()

    return nll, cons
# ----------------------
def _fit(cfg : RXFitConfig) -> None:
    '''
    This is where DataFitter is used
    '''
    ftr = LikelihoodFactory(
        name   = 'main',
        obs    = cfg.observable,
        q2bin  = cfg.q2bin,
        sample = DATA_SAMPLE,
        cfg    = cfg.mod_cfg)
    nll     = ftr.run()
    cfg_mod = ftr.get_config()

    nll, cons = _add_constraints(nll=nll, cfg=cfg)

    ftr = DataFitter(
        q2bin = cfg.q2bin,
        d_nll = {cfg.name : (nll, cfg_mod)}, 
        cfg   = cfg.mod_cfg)
    res = ftr.run()

    if cfg.toy_cfg is None:
        log.info('Not making toys')
        return

    log.info(f'Making {cfg.toy_cfg.ntoys} toys')

    mkr = ToyMaker(
        nll= nll, 
        res= res, 
        cfg= cfg.toy_cfg, 
        cns= cons)
    mkr.get_parameter_information(name = 'rare_ee')
# ----------------------
def main(args : DictConfig | None = None):
    '''
    Entry point
    '''
    with UnpackerModel.package(name = 'fitter_data'):
        cfg = _parse_args(args = args)

    _set_logs()

    client = _get_client(cfg = cfg)
    with ExitStack() as stack:
        if client is not None:
            stack.enter_context(RDFLoader.client(client = client))

        stack.enter_context(Cache.cache_root(path=cfg.output_directory))
        stack.enter_context(PL.parameter_schema(cfg=cfg.mod_cfg.yields))
        stack.enter_context(sel.custom_selection(d_sel=cfg.overriding_selection))

        _fit(cfg=cfg)
# ----------------------
if __name__ == '__main__':
    main()
