'''
Script with tests for PFNReader class
'''
import pytest
from post_ap      import PFNReader, PFNReaderConf
from post_ap      import Production
from dmu          import LogStore
from dmu.generic  import utilities as gut

log=LogStore.add_logger('post_ap:test_pfn_reader')
# ----------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('post_ap:pfn_reader', 10)
# -----------------------------
class Data:
    '''
    Class used to store shared data
    '''
    l_arg_nopid : list[tuple[str,int]] = [
        ('w31_34_v1r3411', 1),
        ('w35_37_v1r3411', 1),
        ('w37_39_v1r3411', 1),
        ('w40_42_v1r3411', 2)]
# -----------------------------
@pytest.mark.parametrize('nickname, expected', Data.l_arg_nopid)
def test_simple(nickname : str, expected : int):
    '''
    Test simple reading
    '''
    data   = gut.load_data(package='post_ap_data', fpath='tests/pfn_reader/simple.yaml')
    cfg    = PFNReaderConf(**data)

    reader = PFNReader(cfg=cfg)
    samples= reader.get_samples(
        production=Production.btoxll_mva_2024_nopid, 
        nickname  =nickname)
    npfn   = samples.size

    assert npfn == expected
# -----------------------------
@pytest.mark.parametrize('analysis', ['rk', 'rkst'])
@pytest.mark.parametrize('sample'  , ['ss_mu', 'ss_md'])
def test_real(analysis : str, sample : str):
    '''
    Test simple reading
    '''
    data    = gut.load_data(package='post_ap_data', fpath=f'post_ap/{analysis}/v4.yaml')
    cfg     = PFNReaderConf(**data)

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_2024, nickname=sample)

    for val in samples.root:
        log.info(val)

    log.info(samples)

    assert samples.size      > 0
    assert len(samples.pfns) > 0
    assert len(samples.pfns) == len(samples.lfns)
# -----------------------------
@pytest.mark.parametrize('sample', ['sim10g_filtered', 'sim10g_unfiltered', 'sim10g_ss'])
def test_sim10g(sample : str):
    '''
    Test simple reading
    '''
    data    = gut.load_data(package='post_ap_data', fpath='post_ap/rx/v15.yaml')
    cfg     = PFNReaderConf(**data)

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_2024, nickname=sample)

    log.info(samples)

    assert samples.size      > 0
    assert len(samples.pfns) > 0
    assert len(samples.pfns) == len(samples.lfns)

