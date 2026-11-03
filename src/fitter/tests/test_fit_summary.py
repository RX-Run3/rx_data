'''
Module with tests for FitSummary class
'''
import os
import pytest

from dmu.stats   import FitResult
from dmu         import LogStore
from fitter      import FitSummary
from typing      import Final
from pathlib     import Path
from rx_common   import Block, Component

from fitter      import FitMetadata
from fitter      import FitSummarizer
from fitter      import FitHarmonizer

log=LogStore.add_logger('fitter:test_fit_summary')

_DATA_PATHS = [
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_500_b3/reso/rk/ee/jpsi/data_24/fit/brem_xx1_brem_xx2/brem_xx2/parameters.json',
]

_SIGN_PATHS = [
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b1/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
    'reso_no_dtf-latest/990_800_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx1/brem_xx1/parameters.json',
    'reso_no_dtf-latest/990_800_b3/reso/rk/ee/jpsi/bpkpjpsiee/fit/brem_xx2/brem_xx2/parameters.json',
]

_DATA_RARE  = [
    'rare_fit_full_scan-low-central/0600-1000_0300-1000_all/rare/rk/ee/low/data_24/fit/brem_x12/brem_x12/parameters.json',
    'rare_fit_full_scan-low-central/0600-1000_0300-1000_all/rare/rk/ee/central/data_24/fit/brem_x12/brem_x12/parameters.json',
    'rare_fit_full_scan-high/0600-1000_0300-1000_all/rare/rk/ee/high/data_24/fit/brem_x12/brem_x12/parameters.json',
]

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# ----------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('fitter:fit_summary', 10)
# ----------------------
@pytest.mark.parametrize('value', _DATA_PATHS + _SIGN_PATHS)
def test_simple(value : str) -> None:
    '''
    Test where overriden path
    '''
    path = _ANADIR / f'fits/data/{value}'

    meta = FitMetadata.from_pars_path(path = path)
    fres = FitResult.from_json(path = path)

    data = [(meta , fres)]
    smr  = FitSummary(root = data)

    assert len(smr.root) > 0
# ----------------------
@pytest.mark.parametrize('value', _DATA_RARE)
def test_rare(value : str) -> None:
    '''
    Test where overriden path
    '''
    path = _ANADIR / f'fits/data/{value}'
    meta = FitMetadata.from_pars_path(path = path)
    fres = FitResult.from_json(path = path)

    hrm  = FitHarmonizer(fres = fres, meta = meta)
    fres = hrm.get_result()

    print(fres)
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest', 'reso_no_dtf-latest'])
def test_summarizer_at(name : str) -> None:
    '''
    Test at method of sumarizer
    '''
    smr = FitSummarizer(name = name, kind = 'reso')
    val = smr.get_summary()

    for meta, fsmr in val.root:
        assert val.at(meta) == fsmr
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest', 'reso_no_dtf-latest'])
def test_save_summary(name : str) -> None:
    '''
    Test at method of sumarizer
    '''
    smr = FitSummarizer(name = name, kind = 'reso')
    smr.get_summary(out_name = 'test.json')

    assert smr.output_path
    assert smr.output_path.exists()
    smr.output_path.unlink()
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest', 'reso_no_dtf-latest'])
def test_merge_summary(name : str) -> None:
    '''
    Test merging summaries
    '''
    smr = FitSummarizer(name = name, kind = 'reso')
    org_summary = smr.get_summary()

    summaries   = org_summary.split(by = 'block')
    mrg_summary = FitSummary.merge(summaries = summaries)

    assert len(org_summary.root) == len(mrg_summary.root)
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest', 'reso_no_dtf-latest'])
def test_process_summary(name : str) -> None:
    '''
    Test merging summaries
    '''
    smr = FitSummarizer(name = name, kind = 'reso')
    smr.get_summary(force_update = True)
# ----------------------
@pytest.mark.parametrize('name', ['reso_dtf-latest', 'reso_no_dtf-latest'])
def test_summarizer_split(name : str) -> None:
    '''
    Test split method of sumarizer
    '''
    smr = FitSummarizer(name = name, kind = 'reso')
    val = smr.get_summary()

    summaries = val.split(by = 'block')

    assert len(summaries) > 0

    nblocks = len(Block.blocks()) # Number of blocks
    fail    = False
    for summary in summaries:
        meta, _ = summary.root[0]
        if meta.component.is_mc: # Background components might be missing in some blocks
            continue

        if len(summary.root) == nblocks:
            continue

        log.error(summary)
        fail = True

    assert not fail
# ----------------------
@pytest.mark.parametrize('value', _DATA_PATHS + _SIGN_PATHS)
def test_at(value : str) -> None:
    '''
    Test at method
    '''
    path = _ANADIR / f'fits/data/{value}'

    meta = FitMetadata.from_pars_path(path = path)
    fres = FitResult.from_json(path = path)

    data = [(meta , fres)]
    smr  = FitSummary(root = data)

    assert smr.at(meta) == fres
# ----------------------
@pytest.mark.parametrize('value', _DATA_PATHS)
def test_grid(value : str) -> None:
    '''
    Test make_grid method
    '''
    comp = Component.bpkpjpsiee
    path = _ANADIR / f'fits/data/{value}'

    meta = FitMetadata.from_pars_path(path = path)
    fres = FitResult.from_json(path = path)

    data = [(meta , fres)]
    smr  = FitSummary(root = data)
    grd  = smr.make_grid(var = f'yld_{comp}_brem_x12', fall_back = None)

    log.info(f'\n{grd.df}')
# ----------------------
