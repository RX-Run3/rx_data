'''
Module with functions that test config classes
'''
import os
os.environ["CUDA_VISIBLE_DEVICES"] = '1'

import pytest

from pathlib     import Path
from dmu         import LogStore
from dmu.stats   import YieldConf
from dmu.generic import utilities as gut
from rx_misid    import MisIDSampleWeights, MisIDSampleSplitting
from rx_common   import Channel, Component, Project, Mass, Qsq
from fitter      import NonParametricConf 
from fitter      import CCbarConf, CombinatorialConf, MisIDConf, ObservableConf, RXFitConfig
from fitter      import ParametricConf
from fitter      import FitModelConf
from fitter      import MVAWp

log=LogStore.add_logger('fitter:test_config')
# ----------------------
@pytest.mark.parametrize('channel', [Channel.ee, Channel.mm  ])
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
@pytest.mark.parametrize('kind'   , ['reso'    , 'rare'      ])
def test_full_config(
    tmp_path: Path,
    kind    : str,
    channel : Channel, 
    project : Project):
    '''
    Test fitting model for data
    '''
    path = f'{kind}/{project}/{channel}/data.yaml'
    cfg  = FitModelConf.from_yaml(path = path, package = 'fitter_data')
    cfg.to_yaml(path = tmp_path / 'config.yaml')

    qsq = Qsq.central if kind == 'rare' else Qsq.jpsi

    cfg = RXFitConfig(
        name    = 'test',
        group   = 'test',
        mva_cmb = MVAWp(0.5),
        mva_prc = MVAWp(0.5),
        q2bin   = qsq,
        mod_cfg = cfg)

    for cfg_cmp in cfg.mod_cfg.components.values():
        assert isinstance(cfg_cmp.cfg_obs, ObservableConf)
# ----------------------
@pytest.mark.parametrize('mass', Mass)
def test_observable_conf(mass : Mass):
    '''
    Test observable configuration
    '''
    cfg = ObservableConf(
        name  = mass, 
        range = (4000, 7000))

    log.info(cfg)
# ----------------------
@pytest.mark.parametrize('analysis', [Project.rk, Project.rkst])
@pytest.mark.parametrize('fname'   , [
    'reso_muon', 
    'reso_electron',
    'rare_muon', 
    'rare_electron',
    'misid_electron',
])
def test_yield_conf(
    fname    : str,
    analysis : Project):
    '''
    Test yield configuration class
    '''
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'model/yields/{analysis}/{fname}.yaml')

    for name, conf in data.items():
        log.info(f'Validating: {name}')
        YieldConf(**conf)
# ----------------------
@pytest.mark.parametrize('analysis', ['rk'  , 'rkst'])
@pytest.mark.parametrize('kind'    , ['reso', 'rare'])
@pytest.mark.parametrize('channel' , ['ee'  ,   'mm'])
def test_combinatorial_sr(
    analysis : str, 
    channel  : str,
    kind     : str):
    '''
    Test for combinatorial in signal region
    '''
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'{kind}/{analysis}/{channel}/comb.yaml')

    CombinatorialConf(**data)
# ----------------------
def test_combinatorial_cr():
    '''
    Test for combinatorial in misid control region
    '''
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = 'misid/rk/ee/comb.yaml')

    CombinatorialConf(**data)
# ----------------------
@pytest.mark.parametrize('analysis', ['rk'  , 'rkst'])
@pytest.mark.parametrize('kind'    , ['reso', 'rare'])
def test_ccbar(analysis : str, kind : str):
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'{kind}/{analysis}/ee/ccbar.yaml')

    CCbarConf(**data)
# ----------------------
@pytest.mark.parametrize('component', [
    Component.bdkstkpiee, 
    Component.bpkstkpiee,
    Component.bsphiee,
    Component.bpkpjpsiee,
    Component.bpkpee])
def test_nonparametric_rare_rk(component : str):
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'rare/rk/ee/{component}_np.yaml')

    NonParametricConf(**data)
# ----------------------
@pytest.mark.parametrize('component', 
        [Component.bdkstkpiee, 
         Component.bdkstkpipsi2ee,
         Component.bdkstkpijpsiee])
def test_nonparametric_rare_rkst(component : Component):
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'rare/rkst/ee/{component}_np.yaml')

    NonParametricConf(**data)
# ----------------------
@pytest.mark.parametrize('component', [Component.bpkpee, Component.bpkpmm])
def test_parametric_rk(component : Component):
    suffix = '.j2'if component == Component.bpkpee else ''
    data   = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'rare/rk/{component.channel}/{component}.yaml{suffix}')

    ParametricConf(**data)
# ----------------------
@pytest.mark.parametrize('component', [Component.bdkstkpiee, Component.bdkstkpimm])
def test_parametric_rkst(component : Component):
    suffix = '.j2'if component == Component.bdkstkpiee else ''
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'rare/rkst/{component.channel}/{component}.yaml{suffix}')

    ParametricConf(**data)
# ----------------------
def test_misid_weights():
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = 'model/weights/weights.yaml')

    MisIDSampleWeights(**data)
# ----------------------
def test_misid_splitting():
    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = 'model/weights/splitting.yaml')

    MisIDSampleSplitting(**data)
# ----------------------
@pytest.mark.parametrize('component', [Component.bpkkk, Component.bpkpipi])
@pytest.mark.parametrize('analysis' , [Project.rk])
def test_misid(
    analysis  : Project,
    component : Component):

    data = gut.load_data(
        package = 'fitter_data', 
        fpath   = f'rare/{analysis}/ee/{component}_np.yaml')

    with MisIDConf.package(name = 'fitter_data'):
        MisIDConf(**data)
# ----------------------
def test_misid_constraint():
    path = Path('misid/rk/ee/data_misid.yaml')

    FitModelConf.from_yaml(
        package = 'fitter_data',
        path    = path)
# ----------------------
@pytest.mark.parametrize('channel', [Channel.ee, Channel.mm  ])
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
@pytest.mark.parametrize('kind'   , ['reso'    , 'rare'      ])
def test_full_model(
    tmp_path: Path,
    kind    : str,
    channel : Channel, 
    project : Project):
    '''
    Test fitting model for data
    '''

    path = f'{kind}/{project}/{channel}/data.yaml'

    cfg = FitModelConf.from_yaml(path = path, package = 'fitter_data')

    cfg.to_yaml(path = tmp_path / 'config.yaml')
# ----------------------
