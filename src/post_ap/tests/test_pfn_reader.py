'''
Script with tests for PFNReader class
'''
import os
import pytest
import tqdm

from pathlib      import Path
from post_ap      import PFNReader, PFNReaderConf
from post_ap      import Production
from post_ap      import Sample
from post_ap      import ProductionConf
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
def _print_tags(sample : Sample):
    for x in sample.data.itertags():
        log.info(x)
# -----------------------------
@pytest.mark.parametrize('nickname, expected', Data.l_arg_nopid)
def test_simple(nickname : str, expected : int):
    '''
    Test simple reading
    '''
    data   = gut.load_data(
        package='post_ap_data', 
        fpath  ='tests/pfn_reader/simple.yaml')
    cfg    = PFNReaderConf(**data)

    reader = PFNReader(cfg=cfg)
    samples= reader.get_samples(
        production=Production.btoxll_mva_2024_nopid, 
        nickname  =nickname)
    npfn   = samples.size

    assert npfn == expected
# -----------------------------
@pytest.mark.parametrize('sample', ['sim10g_ss'])
def test_real(sample : str):
    '''
    Test simple reading
    '''
    data    = gut.load_data(
        package='post_ap_data', 
        fpath  ='post_ap/rx/v15.yaml')
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
    data    = gut.load_data(
        package='post_ap_data', 
        fpath  ='post_ap/rx/v15.yaml')
    cfg     = PFNReaderConf(**data)

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_2024, nickname=sample)

    log.info(samples)

    _print_tags(sample = samples[0])

    assert samples.size      > 0
    assert len(samples.pfns) > 0
    assert len(samples.pfns) == len(samples.lfns)
# -----------------------------
@pytest.mark.parametrize('sample', ['sim10g_unfiltered'])
def test_progress(sample : str):
    '''
    Test that sample container can be iterated
    '''
    data    = gut.load_data(
        package='post_ap_data', 
        fpath  ='post_ap/rx/v15.yaml')
    cfg     = PFNReaderConf(**data)

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(
        production=Production.rx_2024, 
        nickname  =sample)

    for _ in tqdm.tqdm(samples, ascii = ' -'):
        pass

    assert len(samples) > 0
# -----------------------------
@pytest.mark.parametrize('sample_name', ['all'])
def test_merge(sample_name : str, tmp_path : Path):
    '''
    Test that sample container can be iterated
    '''
    cfg_prod = ProductionConf(
        versions = {'all' : 'v1r5849'},
        samples  = {'all' : None},
        fractions= dict(),
    )

    cfg     = PFNReaderConf(
        working_group='RD',
        productions  = {Production.rx_filter : cfg_prod},
    )

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(
        production=Production.rx_filter, 
        nickname  =sample_name)

    sample      = samples[0]
    sample_copy = sample.model_copy(deep = True)
    with gut.environment(mapping = {'ANADIR' : str(tmp_path)}),\
         Sample.storage(value = tmp_path / 'downloaded'):
        for path in sample.target_paths.values():
            assert not path.exists()

        assert not sample.is_merged

        for path in sample.target_paths.values():
            path.parent.mkdir(parents = True, exist_ok = True)
            path.touch()
            log.info(f'Making: {path}')

        assert sample_copy.is_merged
# -----------------------------
@pytest.mark.parametrize('sample', ['sim10g_filtered', 'sim10g_unfiltered', 'sim10g_ss'])
def test_polarity(sample : str):
    '''
    Test getting path associated to sample
    '''
    data    = gut.load_data(
        package='post_ap_data', 
        fpath  ='post_ap/rx/v15.yaml')
    cfg     = PFNReaderConf(**data)

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_2024, nickname=sample)

    for sam in samples:
        assert sam.polarity in {'magup', 'magdown'}
        log.info(sam.polarity)
# -----------------------------
def test_paths():
    '''
    Test getting path associated to sample
    '''
    prod_cfg= ProductionConf(
        versions = {'all' : 'v1r5849'},
        samples  = {'all' : None},
        fractions= {'all' : None})

    cfg     = PFNReaderConf(
        working_group= 'RD', 
        productions  = {Production.rx_filter : prod_cfg})

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_filter, nickname='all')
    sample  = samples.root[0]

    ANADIR       = os.environ['ANADIR']
    storage_path = ANADIR / Path('downloaded')
    with Sample.storage(value = storage_path):
        for sample in samples:
            log.info(sample)
# -----------------------------
def test_trigger():
    '''
    Test getting path associated to sample
    '''
    prod_cfg= ProductionConf(
        versions = {'all' : 'v1r5849'},
        samples  = {'all' : None},
        fractions= {'all' : None})

    cfg     = PFNReaderConf(
        working_group= 'RD', 
        productions  = {Production.rx_filter : prod_cfg})

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_filter, nickname='all')
    sample  = samples.root[0]

    ANADIR       = os.environ['ANADIR']
    storage_path = ANADIR / Path('downloaded')
    with Sample.storage(value = storage_path):
        for sample in samples:
            log.info(sample.name)
            for trigger in sample.triggers:
                log.info(f'    {trigger}')
# -----------------------------
def test_target_paths():
    '''
    Test getting path associated to sample
    '''
    prod_cfg= ProductionConf(
        versions = {'all' : 'v1r5849'},
        samples  = {'all' : None},
        fractions= {'all' : None})

    cfg     = PFNReaderConf(
        working_group= 'RD', 
        productions  = {Production.rx_filter : prod_cfg})

    reader  = PFNReader(cfg=cfg)
    samples = reader.get_samples(production=Production.rx_filter, nickname='all')
    sample  = samples.root[0]

    ANADIR       = os.environ['ANADIR']
    storage_path = ANADIR / Path('downloaded')
    with Sample.storage(value = storage_path):
        for sample in samples:
            log.info(sample.name)
            log.info(f'   {sample.target_paths}')

