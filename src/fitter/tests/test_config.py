'''
Module with functions that test config classes
'''
import pytest

from typing      import Any
from pydantic    import TypeAdapter
from pathlib     import Path
from dmu         import LogStore, LogLevels
from dmu.stats   import CompositeYieldConf
from dmu.stats   import SimpleYieldConf
from dmu.generic import UnpackerModel, utilities as gut
from rx_misid    import MisIDSampleWeights, MisIDSampleSplitting
from rx_common   import Channel, Component, Project, Mass, Qsq, Brem
from rx_common   import MVAWp
from fitter      import NonParametricConf
from fitter      import CCbarConf, CombinatorialConf, MisIDConf, ObservableConf, RXFitConfig
from fitter      import ParametricConf
from fitter      import FitModelConf
from fitter      import ModelSystematics
from fitter      import CmbConstraintConf
from fitter      import CombinatorialConfUnconstrained

log=LogStore.add_logger('fitter:test_config')
# ----------------------
@pytest.fixture(autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:configs', LogLevels.debug)
    with UnpackerModel.package(name = 'fitter_data'):
        yield
# ----------------------
def test_swap():
    '''
    Test loading config for track swapped control regions
    '''
    data = gut.load_data(package = 'fitter_data', fpath = 'rare/rk/mm/kmm_mkm/data.yaml')
    FitModelConf(**data)
# ----------------------
@pytest.mark.parametrize('channel', [Channel.ee, Channel.mm  ])
@pytest.mark.parametrize('project', [Project.rk, Project.rkst])
@pytest.mark.parametrize('q2bin'  , Qsq.for_physics())
@pytest.mark.parametrize('mva_wp' , [MVAWp(root = 0.5), MVAWp.none()])
def test_full_config(
    monkeypatch,
    tmp_path: Path,
    q2bin   : Qsq,
    mva_wp  : MVAWp,
    channel : Channel,
    project : Project):
    '''
    Test fitting model for data
    '''
    monkeypatch.setenv('ANADIR', str(tmp_path))

    path = f'{q2bin.kind}/{project}/{channel}/data.yaml'
    cfg  = FitModelConf.from_yaml(path = path, package = 'fitter_data')
    cfg.to_yaml(path = tmp_path / 'config.yaml')

    cfg = RXFitConfig(
        name    = 'test',
        group   = 'test',
        mva_cmb = mva_wp,
        mva_prc = mva_wp,
        q2bin   = q2bin,
        mod_cfg = cfg)

    for cfg_cmp in cfg.mod_cfg.components[q2bin].values():
        assert isinstance(cfg_cmp.cfg_obs, ObservableConf)

    if mva_wp != MVAWp.none():
        return

    with pytest.raises(ValueError):
        _ = cfg.cmb_cut

    with pytest.raises(ValueError):
        _ = cfg.prc_cut
# ----------------------
@pytest.mark.parametrize('mass', Mass)
def test_observable_conf(mass : Mass):
    '''
    Test observable configuration
    '''
    cfg = ObservableConf(
        mass  = mass,
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
    data : dict[str,Any] = gut.load_data(
        package = 'fitter_data',
        fpath   = f'model/yields/{analysis}/{fname}.yaml')

    yield_adapter = TypeAdapter(SimpleYieldConf | CompositeYieldConf)
    for name, conf in data.items():
        log.info(f'Validating: {name}')
        yield_adapter.validate_python(conf)
# ----------------------
@pytest.mark.parametrize('analysis', ['rk'  , 'rkst'])
@pytest.mark.parametrize('kind'    , ['reso', 'rare'])
@pytest.mark.parametrize('channel' , ['ee'  ,   'mm'])
@pytest.mark.parametrize('name'    , ['comb', 'comb_alt_1'])
def test_combinatorial_sr(
    name     : str,
    analysis : str,
    channel  : str,
    kind     : str):
    '''
    Test for combinatorial in signal region
    '''
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = f'{kind}/{analysis}/{channel}/{name}.yaml')

    if   kind == 'rare' and channel == 'ee':
        obj = CombinatorialConf(**data)
        assert isinstance(obj.constraints, CmbConstraintConf)
    elif kind == 'reso'  or channel == 'mm':
        obj = CombinatorialConfUnconstrained(**data)
    else:
        raise ValueError(f'Invalid kind: {kind}')

    assert isinstance(obj.models, dict)
# ----------------------
@pytest.mark.parametrize('analysis', ['rk'  , 'rkst'])
@pytest.mark.parametrize('name'    , ['comb_ss', 'comb_ss_alt_1'])
def test_combinatorial_ss(
    name     : str,
    analysis : str):
    '''
    Test for combinatorial in signal region
    '''
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = f'rare/{analysis}/ee/{name}.yaml')

    CombinatorialConfUnconstrained(**data)
# ----------------------
def test_combinatorial_cr():
    '''
    Test for combinatorial in misid control region
    '''
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = 'misid/rk/ee/comb.yaml')

    CombinatorialConfUnconstrained(**data)
# ----------------------
@pytest.mark.parametrize('analysis', ['rk'  , 'rkst'])
@pytest.mark.parametrize('kind'    , ['reso', 'rare'])
def test_ccbar(analysis : str, kind : str):
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = f'{kind}/{analysis}/ee/ccbar.yaml')

    obj = CCbarConf(**data)
    print(obj)
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

    cfg = ParametricConf(**data)
    if component.channel == Channel.ee:
        cfg = cfg.cfg_clone(prefix = 'BREM', brems = [Brem.one, Brem.two])
# ----------------------
@pytest.mark.parametrize('component', [Component.bdkstkpiee, Component.bdkstkpimm])
def test_parametric_rkst(component : Component):
    suffix = '.j2'if component == Component.bdkstkpiee else ''
    data = gut.load_data(
        package = 'fitter_data',
        fpath   = f'rare/rkst/{component.channel}/{component}.yaml{suffix}')

    cfg = ParametricConf(**data)
    if component.channel == Channel.ee:
        cfg = cfg.cfg_clone(prefix = 'BREM', brems = [Brem.one, Brem.two])
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
@pytest.mark.parametrize('q2bin'  , Qsq.for_physics())
def test_full_model(
    tmp_path: Path,
    q2bin   : Qsq,
    channel : Channel,
    project : Project):
    '''
    Test fitting model for data
    '''
    path = f'{q2bin.kind}/{project}/{channel}/data.yaml'
    cfg  = FitModelConf.from_yaml(path = path, package = 'fitter_data')
    if channel == Channel.ee and q2bin.is_rare:
        cfg = cfg.cfg_clone(
            q2bin   = q2bin,
            prefix  = 'BREM',
            brems   = [Brem.one, Brem.two])

    cfg.to_yaml(path = tmp_path / 'config.yaml')
# ----------------------
def test_model_systematics():
    '''
    Test ModelSystematics class
    '''
    obj = ModelSystematics.load()
    for systematic in obj.root:
        mod = obj.get(systematic)
        assert len(mod) == len(systematic.entries)
# ----------------------
