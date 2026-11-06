'''
Module with unit tests for functions in dmu.stat.utilities
'''
import os
import re
import pytest
import numpy

from importlib.resources    import files
from pathlib                import Path
from typing                 import Literal, Final

from dmu          import LogStore
from dmu.stats    import utilities as sut
from dmu.stats    import zfit
from dmu.stats    import Fitter
from dmu.stats    import print_pdf
from dmu.stats    import pdf_to_tex
from dmu.stats    import is_pdf_usable
from dmu.stats    import ZFitPlotterConf
from dmu.generic  import rxran
from dmu.testing  import get_nll, get_model
from zfit.data    import Data     as zdata
from zfit.pdf     import BasePDF  as zpdf
from zfit         import dill

log = LogStore.add_logger('dmu:tests:stats:test_utilities')

_FLOAT_TOLERANCE : Final[float] = 1e-5
#----------------------------------
class Data:
    '''
    Class needed to hold shared variables
    '''
    user    = os.environ['USER']
#----------------------------------
@pytest.fixture(scope='session', autouse=True)
def initialize():
    '''
    This will run before any test
    '''
    LogStore.set_level('dmu:stats:utilities', 10)

    with rxran.seed(42):
        yield
#----------------------------------
def _get_pdf_simple(is_extended : bool = True) -> zpdf:
    obs = zfit.Space('m',    limits=(-10, 10))
    mu  = zfit.Parameter("mu_gaus_test_1", 0.4,   -5,     5)
    sg  = zfit.Parameter("sg_gaus_test_1", 1.3,  0.5,     2)
    ne  = zfit.Parameter('ne_gaus_test_1',  10,    1, 10000)

    sg.floating = False

    pdf  = zfit.pdf.Gauss(obs=obs, mu=mu, sigma=sg)
    if not is_extended:
        return pdf

    epdf = pdf.create_extended(ne)

    return epdf
#----------------------------------
def _get_pdf_composed_nonextended() -> zpdf:
    obs = zfit.Space('m', limits=(-10, 10))
    mu1 = zfit.Parameter("mu1", 0.4, -5, 5)
    sg1 = zfit.Parameter("sg1", 1.3,  0, 5)
    mu2 = zfit.Parameter("mu2", 0.4, -5, 5)
    sg2 = zfit.Parameter("sg2", 1.3,  0, 5)

    pd1 = zfit.pdf.Gauss(obs=obs, mu=mu1, sigma=sg1, name='gauss1')
    fr1 = zfit.Parameter('fr1', 0.5, 0, 1)

    pd2 = zfit.pdf.Gauss(obs=obs, mu=mu2, sigma=sg2, name='gauss2')
    fr2 = zfit.Parameter('fr2', 0.5, 0, 1)

    pdf = zfit.pdf.SumPDF([pd1, pd2], fracs=[fr1, fr2])

    return pdf
#----------------------------------
def _get_zdata(weighted : bool) -> tuple[zdata, float]:
    '''
    Returns zfit data, weighted or not and yield
    '''
    arr_val = numpy.random.uniform(0, 1 , size=100)
    if weighted:
        arr_wgt = numpy.random.normal(1, 0.1, size=100)
        target  = arr_wgt.sum()
    else:
        arr_wgt = None
        target  = 100

    obs  = zfit.Space('x', limits=(0, 1))
    data = zfit.Data.from_numpy(obs=obs, array=arr_val, weights=arr_wgt)

    if not isinstance(data, zdata):
        raise ValueError('No zfit ata found')

    return data, target
#----------------------------------
def _get_pdf(kind : str ='simple') -> zpdf:
    if   kind == 'simple':
        return _get_pdf_simple()

    if kind == 'composed_nonextended':
        return _get_pdf_composed_nonextended()

    raise ValueError(f'Invalid PDF kind: {kind}')
#----------------------------------
def test_print_pdf(tmp_path : Path):
    '''
    Tests for PDF printer
    '''
    pdf = _get_pdf(kind='composed_nonextended')

    d_const = {'mu1' : (0.0, 0.1), 'sg1' : (1.0, 0.1)}
    #-----------------
    print_pdf(pdf)

    print_pdf(pdf,
        blind   = ['sg.*', 'mu.*'])

    print_pdf(pdf,
        d_const = d_const,
        blind   = ['sg.*', 'mu.*'])
    #-----------------
    print_pdf(pdf,
        txt_path = f'{tmp_path}/utilities/print_pdf/pdf.txt')

    print_pdf(pdf,
        blind    =['sg.*', 'mu.*'],
        txt_path = f'{tmp_path}/utilities/print_pdf/pdf_blind.txt')

    print_pdf(pdf,
        d_const  = d_const,
        txt_path = f'{tmp_path}/utilities/print_pdf/pdf_const.txt')
# ----------------------
def test_blind_manager():
    '''
    Tests blinded_variables context manager
    '''
    pdf   = _get_pdf(kind='composed_nonextended')
    regex = r'mu.*'

    with sut.blinded_variables(regex_list=[regex]):
        l_msg = print_pdf(pdf=pdf)

    assert isinstance(l_msg, list)

    for line in l_msg:
        assert not re.match(regex, line)
#----------------------------------
def test_pdf_to_tex(tmp_path : Path):
    '''
    Tests converting text file with PDF description
    into latex table
    '''
    d_par = {
        'ar_dscb_Signal_002_1_reso_flt' : r'$\alpha_{DSCB}^{1}$',
        'c_exp_cmb_1'                   : 'b',
        'frac_brem_001'                 : 'c',
        'mu_Signal_001_scale_flt'       : 'd',
        'mu_Signal_002_scale_flt'       : 'e',
        }

    data    = files('dmu_data').joinpath('tests/pdf_to_tex.txt')
    in_path = Path(str(data))

    pdf_to_tex(
        in_path = in_path,
        out_dir = tmp_path,
        d_par   = d_par)
#----------------------------------
def test_is_pdf_usable():
    '''
    Tests for PDF printer
    '''
    pdf = _get_pdf(kind='composed_nonextended')

    is_pdf_usable(pdf=pdf)
#----------------------------------
@pytest.mark.parametrize('is_extended', [True, False])
def test_save_fit_simple(tmp_path : Path, is_extended : bool):
    '''
    Simplest case
    '''
    pdf = _get_pdf_simple(is_extended=is_extended)
    dat = pdf.create_sampler(n=1000)

    obj = Fitter(pdf, dat)
    res = obj.fit()

    cfg = ZFitPlotterConf(
        nbins      = 50,
        stacked    = True,
        plot_range = (-5, +6),
    )

    sut.save_fit(
        data   =dat,
        model  =pdf,
        res    =res,
        plt_cfg=cfg,
        fit_dir=tmp_path)
#----------------------------------
def test_save_fit_empty(tmp_path : Path):
    '''
    Simplest case
    '''
    pdf = _get_pdf_simple()
    dat = pdf.create_sampler(n=0)

    cfg = ZFitPlotterConf(
        nbins      = 50,
        stacked    = True,
        plot_range = (-5, +6),
    )

    sut.save_fit(
        data    = dat,
        model   = pdf,
        res     = None,
        plt_cfg = cfg,
        fit_dir = tmp_path)
#----------------------------------
def test_save_fit_param(tmp_path : Path):
    '''
    Tests saving fit with parameters
    '''
    pdf = _get_pdf(kind='simple')
    dat = pdf.create_sampler(n=1000)

    obj = Fitter(pdf, dat)
    res = obj.fit()

    cfg = ZFitPlotterConf(
        nbins   = 50,
        stacked = True)

    sut.save_fit(
        data   = dat,
        model  = pdf,
        res    = res,
        plt_cfg= cfg,
        fit_dir= tmp_path)
#----------------------------------
def test_save_fit_nomodel(tmp_path : Path):
    '''
    Tests saving fit without model
    '''
    pdf = _get_pdf(kind='simple')
    dat = pdf.create_sampler(n=1000)

    cfg = ZFitPlotterConf(
        nbins   = 50,
        stacked = True)

    sut.save_fit(
        data   =dat,
        model  =None,
        res    =None,
        plt_cfg=cfg,
        fit_dir=tmp_path)
#----------------------------------
def test_name_from_obs():
    '''
    Tests retrieval of name from observable
    '''
    obs  = zfit.Space('xyz', limits=(0, 10))
    name = sut.name_from_obs(obs=obs)

    assert name == 'xyz'
#----------------------------------
def test_range_from_obs():
    '''
    Tests retrieval of range from observable
    '''
    MAX = 10
    MIN =  0

    obs        = zfit.Space('xyz', limits=(MIN, MAX))
    minx, maxx = sut.range_from_obs(obs=obs)

    assert minx == MIN
    assert maxx == MAX
#----------------------------------
@pytest.mark.parametrize('weighted', [True, False])
def test_yield_from_zdata(weighted : bool):
    '''
    Tests function that does retrieval of yield from zfit data
    '''
    data, target = _get_zdata(weighted=weighted)

    val = sut.yield_from_zdata(data=data)

    assert abs(val - target) < _FLOAT_TOLERANCE
#----------------------------------
def test_save_nll(tmp_path : Path):
    '''
    Saves NLL to temporary path
    '''
    nll  = get_nll(kind = 's+b', suffix = '')
    path = sut.save_nll(loss = nll, path = tmp_path / 'nll.bytes')

    log.info(f'Saving NLL to: {path}')

    assert path.exists()

    nll_bytes = path.read_bytes()
    nll       = dill.loads(nll_bytes)

    minimizer = zfit.minimize.Minuit()
    res = minimizer.minimize(loss = nll)
    print(res)
#----------------------------------
def test_save_nll_context(tmp_path : Path):
    '''
    Saves NLL to temporary path set by context manager
    '''
    root_dir = tmp_path / 'alternative_context'

    nll  = get_nll(kind = 's+b', suffix = '')
    with sut.root_directory(root_dir = root_dir):
        path = sut.save_nll(loss = nll)

    log.info(f'Saving NLL to: {path}')

    assert path.exists()

    nll_bytes = path.read_bytes()
    nll       = dill.loads(nll_bytes)

    minimizer = zfit.minimize.Minuit()
    res = minimizer.minimize(loss = nll)
    print(res)
#----------------------------------
@pytest.mark.parametrize('pair', ['by_name', 'by_order'])
def test_merge_sum_models(pair : Literal['by_name', 'by_order']):
    '''
    Test merging models
    '''
    obs   = zfit.Space(obs = 'mass', limits = (-10, 10))
    pdf_a = get_model(kind = 's+b', suffix = 'a', obs = obs, suffix_pdfs = pair == 'by_order')
    pdf_b = get_model(kind = 's+b', suffix = 'b', obs = obs, suffix_pdfs = pair == 'by_order')
    pdf_c = get_model(kind = 's+b', suffix = 'c', obs = obs, suffix_pdfs = pair == 'by_order')

    pdf   = sut.merge_sum_models(
        obs    = obs,
        pair   = pair,
        models = [pdf_a, pdf_b, pdf_c])

    print_pdf(pdf = pdf)
#----------------------------------
@pytest.mark.parametrize('pair', ['by_name', 'by_order', 'by_prefix'])
def test_merge_sum_models_missing(pair : Literal['by_name', 'by_order', 'by_prefix']):
    '''
    Test merging models with one component missing in one region
    '''
    obs   = zfit.Space(obs = 'mass'  , limits = (-10, 10))
    pdf_a = get_model(kind = 's+b+x' , suffix = 'a', obs = obs, suffix_pdfs = pair != 'by_name')
    pdf_b = get_model(kind = 's+b'   , suffix = 'b', obs = obs, suffix_pdfs = pair != 'by_name')
    pdf_c = get_model(kind = 's+b'   , suffix = 'c', obs = obs, suffix_pdfs = pair != 'by_name')

    prefixes = ['signal', 'signal_alt', 'bkg']

    if pair != 'by_prefix':
        with pytest.raises(ValueError):
            pdf = sut.merge_sum_models(
                obs    = obs,
                models = [pdf_a, pdf_b, pdf_c],
                pair   = pair)
    else:
        pdf = sut.merge_sum_models(
            obs      = obs,
            pair     = pair,
            prefixes = prefixes,
            models   = [pdf_a, pdf_b, pdf_c])

        print_pdf(pdf = pdf)
#----------------------------------

