'''
Module holding tests for SampleEmulator class
'''
import json
import numpy
import pytest

from typing      import Final
from ROOT        import RDataFrame, RDF
from dmu         import LogStore
from dmu.generic import utilities as gut
from rx_common   import Component
from rx_data     import SampleEmulator
from rx_data     import EmulatorConf
from rx_data     import SamplesConf

log=LogStore.add_logger('rx_data:test_sample_emulator')

type Components = list[Component]
type Pairs      = list[tuple[Component, Component]]

_KAON_ID     : Final[int] = 321
_PION_ID     : Final[int] = 211
_ELECTRON_ID : Final[int] = 11

_SWAPPED_TRACKS : Final[Components] = [
    Component.bpkpjpsiee_kee_eke,
    Component.bdkstkpijpsiee_kpiee_pikee,
    Component.bdkstkpijpsiee_kpiee_epiek,
    Component.bdkstkpijpsiee_kpiee_kepie,
]

_SAMPLES_CONCATENATE : Final[Components] = [
    Component.bpkxkpipiee,
]

_SAMPLES_MOTHER_SWAP : Final[Components] = [
    Component.bskstjpsimm,
    Component.bskstjpsiee,
]

_SAMPLE_PAIRS : Final[Pairs] = [
    (Component.bskstjpsimm, Component.bdkstkpijpsimm),
    (Component.bskstjpsiee, Component.bdkstkpijpsiee),
    (Component.bskstpsi2mm, Component.bdkstkpipsi2mm),
    (Component.bskstpsi2ee, Component.bdkstkpipsi2ee),
]

_SWAPPED_MASSES : Final[list[str]] = [
    'B_M',
    'B_Mass',
    'B_const_mass_M',
    'B_const_mass_psi2S_M',
]
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('rx_data:sample_emulator', 10)
    LogStore.set_level('dmu:generic:utilities'  , 10)
# ----------------------
def _get_rdf(size : int = 10) -> RDF.RNode:
    '''
    Returns
    -------------
    Dataframe with zeroed columns 
    '''
    rdf = RDataFrame(size)

    if size == 0:
        return rdf

    rdf = rdf.Define('B_M'                 ,   '0')
    rdf = rdf.Define('Kst_M'               ,   '0')
    rdf = rdf.Define('B_Mass'              ,   '0')
    rdf = rdf.Define('B_const_mass_M'      ,   '0')
    rdf = rdf.Define('B_const_mass_psi2S_M',   '0')
    rdf = rdf.Define('B_TRUEID'            , '123')
    rdf = rdf.Define('B_ID'                , '123')
    rdf = rdf.Define('Kst_MC_MOTHER_ID'    , '123')
    rdf = rdf.Define('Jpsi_MC_MOTHER_ID'   , '123')
    # --------------------------
    rdf = rdf.Define('H_ID'                , '321')
    rdf = rdf.Define('H_PT'                , '10000')
    rdf = rdf.Define('H_ETA'               , '2.0')
    rdf = rdf.Define('H_PHI'               , '1.0')
    # --------------------------
    rdf = rdf.Define('H1_ID'               , '321')
    rdf = rdf.Define('H1_PT'               , '10000')
    rdf = rdf.Define('H1_ETA'              , '2.0')
    rdf = rdf.Define('H1_PHI'              , '1.0')
    # --------------------------
    rdf = rdf.Define('H2_ID'               , '-211')
    rdf = rdf.Define('H2_PT'               , '20000')
    rdf = rdf.Define('H2_ETA'              , '2.0')
    rdf = rdf.Define('H2_PHI'              , '1.0')
    # --------------------------
    rdf = rdf.Define('L1_ID'               , '-11')
    rdf = rdf.Define('L1_PT'               , '10000')
    rdf = rdf.Define('L1_ETA'              , '2.0')
    rdf = rdf.Define('L1_PHI'              , '1.0')
    # --------------------------
    rdf = rdf.Define('L2_ID'               , '11')
    rdf = rdf.Define('L2_PT'               , '20000')
    rdf = rdf.Define('L2_ETA'              , '2.0')
    rdf = rdf.Define('L2_PHI'              , '1.0')
    # --------------------------

    return rdf
# --------------------------------------------
def test_samples_conf():
    '''
    Test config used to represent samples
    '''
    for component in Component:
        if not component.has_sample: 
            continue

        cfg = SamplesConf({component : 1.0})
        assert not cfg.is_cocktail
        assert cfg.is_data != component.is_mc
        assert component in cfg.root

    cfg = SamplesConf({
            Component.bpk1kpipiee : 0.5,
            Component.bpk2kpipiee : 0.5,
         })

    assert cfg.is_cocktail
# --------------------------------------------
def test_emulator_conf():
    '''
    Test loading config
    '''
    data = gut.load_data(
        package = 'rx_data_data', 
        fpath   = 'emulated_trees/config.yaml')
    data_str = json.dumps(data)

    obj  = EmulatorConf.model_validate_json(data_str)

    assert obj is not None
# --------------------------------------------
@pytest.mark.parametrize('sample', _SAMPLES_CONCATENATE)
def test_concatenate(sample : Component):
    '''
    Test with samples resulting from concatenation of other samples
    '''
    emu = SampleEmulator(sample=sample)

    assert len(emu.samples.root) > 1
# --------------------------------------------
@pytest.mark.parametrize('new_name, old_name', _SAMPLE_PAIRS)
def test_rename(
    new_name : Component, 
    old_name : Component):
    '''
    Check renaming of samples

    new_name: Sample requested 
    old_name: Sample that will emulate sample requested 
    '''
    emu = SampleEmulator(sample=new_name)

    assert emu.samples.emulated_only_by(sample = old_name)
# --------------------------------------------
@pytest.mark.parametrize('sample', _SAMPLES_MOTHER_SWAP)
@pytest.mark.parametrize('size'  , [0, 100])
def test_swap_mother(sample : Component, size : int):
    '''
    sample: Name of sample to emulate
    '''
    log.info('')
    rdf_old = _get_rdf(size = size)
    emu     = SampleEmulator(sample=sample)
    rdf_new = emu.post_process(rdf = rdf_old)

    data    = rdf_new.AsNumpy()
    expected= 87.23 # Mass difference between Bs and Bd
    for name, arr_val in data.items():
        if name not in _SWAPPED_MASSES:
            continue

        assert numpy.isclose(arr_val, expected).all()
# --------------------------------------------
@pytest.mark.parametrize('sample', _SWAPPED_TRACKS)
def test_swap_tracks(sample : Component):
    '''
    sample: Name of sample to emulate
    '''
    size    = 1000

    log.info('')
    rdf_old = _get_rdf(size = size)
    emu     = SampleEmulator(sample=sample)
    rdf_new = emu.post_process(rdf = rdf_old)

    data = rdf_new.AsNumpy()
    for col in data:
        log.info(col)

    if sample == Component.bdkstkpijpsiee_kpiee_pikee:
        assert all(data['H1_ID'] == -_PION_ID)
        assert all(data['H2_ID'] ==  _KAON_ID)

    if sample == Component.bpkpjpsiee_kee_eke:
        assert all(data['L1_ID'] ==   _KAON_ID)
        assert all(data['H_ID' ] == - _ELECTRON_ID)
# --------------------------------------------
