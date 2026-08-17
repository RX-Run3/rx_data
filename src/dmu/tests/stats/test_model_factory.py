'''
Module containing tests for ZModel class
'''
import matplotlib.pyplot as plt
import pytest
import numpy

from pathlib     import Path
from dmu         import LogStore
from dmu.stats   import zfit
from dmu.stats   import print_pdf
from dmu.stats   import ModelFactory, MethodRegistry
from dmu.stats   import ModelFactoryConf
from dmu.stats   import ParameterLibrary
from dmu.stats   import Model
from dmu.stats   import CorrectionImplementation
from dmu.stats   import ZFitPlotter, ZFitPlotterConf
from dmu.stats   import utilities  as sut
from zfit.pdf    import BasePDF    as zpdf

log=LogStore.add_logger('dmu:stats:test_model_factory')
#--------------------------
class Data:
    '''
    Data class used to share
    '''
    obs = zfit.Space('mass', limits=(5080, 5680))

    l_arg_run3 = [
            ('2024', 'ETOS', 'ctrl'),
            ]

    l_arg_simple = [
            ('2018', 'MTOS', 'ctrl'),
            ('2018', 'MTOS', 'psi2'),
            ('2018', 'ETOS', 'ctrl'),
            ('2018', 'ETOS', 'psi2'),
            ]

    l_arg_syst = [
            ('2018', 'MTOS', 'ctrl'),
            ('2018', 'ETOS', 'ctrl'),
            ]

    l_arg_prc = [
            ('2018', 'ETOS', 'ctrl'),
            ('2018', 'ETOS', 'psi2'),
            ]

    l_arg_signal = [
            ('2018', 'ETOS', 'ctrl'),
            ('2018', 'ETOS', 'psi2'),
            ('2018', 'MTOS', 'ctrl'),
            ('2018', 'MTOS', 'psi2'),
            ]
#--------------------------
@pytest.fixture(scope='module', autouse=True)
def initialize():
    '''
    This runs before tests
    '''
    LogStore.set_level('dmu:stats:model_factory', 10)
    LogStore.set_level('dmu:parameters'         , 10)
# ----------------------
def _check_reparametrized_pdf(
    pdf        : zpdf,
    fix_scales : bool) -> None:
    '''
    Parameters
    -------------
    pdf: zfit PDF
    scales_must_float: If true, assert that scales are floating
    '''
    all_params = pdf.get_params(floating = True) | pdf.get_params(floating = False)
    params     = [ par for par in all_params if par.name.endswith('_flt') ]

    assert len(params) == 2

    par_scale  = params[0] if params[0].name.endswith('scale_flt') else params[1]
    par_reso   = params[0] if params[0].name.endswith( 'reso_flt') else params[1]

    assert 'scale_flt' in par_scale.name
    assert  'reso_flt' in par_reso.name

    if fix_scales:
        assert not par_scale.floating
        assert not par_reso.floating
    else:
        assert par_scale.floating
        assert par_reso.floating
#--------------------------
def _add_pdfs(l_pdf : list[zpdf]) -> None:
    l_par = [ zfit.param.Parameter(f'p{pdf.name}', 500, 0, 1000) for pdf in l_pdf ]

    zfit.pdf.SumPDF(l_pdf, l_par)
#--------------------------
def test_values():
    '''
    Test passing ranges for parameters
    '''
    l_pdf = [Model.cbr, Model.cbl, Model.dscb]
    l_shr = ['mu', 'sg']
    l_flt = ['mu', 'sg']

    MU_VAL = 5522
    MU_LOW = 5511
    MU_HIG = 6033

    SG_VAL = 11.1 
    SG_LOW =  3.3 
    SG_HIG = 20.2 

    values= {
        'mu' : (MU_VAL, MU_LOW, MU_HIG),
        'sg' : (SG_VAL, SG_LOW, SG_HIG),
    }

    mod   = ModelFactory(
        preffix = 'unique',
        obs     = Data.obs,
        l_pdf   = l_pdf,
        d_fix   = {'al_dscb' : 3, 'nr_dscb' : 1},
        values  = values,
        l_shared= l_shr,
        l_float = l_flt)

    pdf = mod.get_pdf()

    [mu] = [ par for par in pdf.get_params() if par.name.startswith('mu_') ]
    [sg] = [ par for par in pdf.get_params() if par.name.startswith('sg_') ]

    assert mu.value().numpy() == MU_VAL
    assert mu.lower.numpy()   == MU_LOW # type: ignore
    assert mu.upper.numpy()   == MU_HIG # type: ignore

    assert sg.value().numpy() == SG_VAL
    assert sg.lower.numpy()   == SG_LOW # type: ignore
    assert sg.upper.numpy()   == SG_HIG # type: ignore

    print_pdf(pdf)
#--------------------------
def test_fix_params():
    '''
    Will test fixing subset of parameters
    '''
    l_pdf = [Model.cbr, Model.cbl, Model.dscb]
    l_shr = ['mu', 'sg']
    l_flt = ['mu', 'sg']

    mod   = ModelFactory(
        preffix = 'unique',
        obs     = Data.obs,
        l_pdf   = l_pdf,
        d_fix   = {'al_dscb' : 3, 'nr_dscb' : 1},
        l_shared= l_shr,
        l_float = l_flt)

    pdf   = mod.get_pdf()

    print_pdf(pdf)
#--------------------------
def test_ipatia(tmp_path : Path):
    mod   = ModelFactory(
        preffix = '',
        obs     = Data.obs,
        l_pdf   = [Model.ipatia],
        l_shared= [],
        l_float = [])
    pdf   = mod.get_pdf()
    sut.print_pdf(pdf = pdf)

    xs = numpy.linspace(5000, 5600, 200)
    ys = pdf.pdf(xs)

    assert not numpy.isnan(ys).all()

    plt.scatter(xs, ys, s = 1)
    plt.savefig(tmp_path / 'plot.png')

    data = pdf.create_sampler(n=10_000)
    nll  = zfit.loss.UnbinnedNLL(model=pdf, data=data)
    
    minimizer = zfit.minimize.Minuit()
    res = minimizer.minimize(nll)

    cfg = ZFitPlotterConf.default()
    ptr = ZFitPlotter(data = data, model = pdf)
    ptr.run(cfg = cfg)
    plt.savefig(tmp_path / 'fit.png')

    print(res)
#--------------------------
def test_unique_pdf():
    '''
    Will test only signal builder
    '''
    l_pdf = [Model.cbr, Model.cbl, Model.dscb]
    l_shr = ['mu', 'sg']
    l_flt = ['mu', 'sg']
    mod   = ModelFactory(preffix = 'unique',
                         obs     = Data.obs,
                         l_pdf   = l_pdf,
                         l_shared= l_shr,
                         l_float = l_flt)

    pdf   = mod.get_pdf()

    print_pdf(pdf)
#--------------------------
def test_repeated_pdf():
    '''
    Will test only signal builder
    '''
    log.info('Testing for repeated PDFs')

    l_pdf = [Model.cbr] + 2 * [Model.cbl]
    l_shr = ['mu', 'sg']
    l_flt = ['mu']
    mod   = ModelFactory(
            preffix = 'repeated',
            obs     = Data.obs,
            l_pdf   = l_pdf,
            l_shared= l_shr,
            l_float = l_flt)
    pdf   = mod.get_pdf()

    print_pdf(pdf)
#--------------------------
@pytest.mark.parametrize('name', MethodRegistry.get_pdf_names())
def test_all_pdf(name : Model):
    '''
    Will create a PDF for each of the models supported
    '''
    log.info(f'Testing {name}')

    l_shr = []
    l_flt = []

    mod   = ModelFactory(
        preffix = '',
        obs     = Data.obs,
        l_pdf   = [name],
        l_shared= l_shr,
        l_float = l_flt)
    pdf   = mod.get_pdf()

    print_pdf(pdf)
#--------------------------
@pytest.mark.parametrize(
    'pdfs', [
    [Model.qgauss],
    [Model.gauss],
    [Model.cbl],
    [Model.cbr],
    [Model.dscb],
    [Model.cbl, Model.cbl],
    [Model.cbl, Model.cbr],
])
@pytest.mark.parametrize(
    'fix_scales', 
    [True, False])
def test_rep_signal(
    fix_scales : bool,
    pdfs       : list[Model]):
    '''
    Test reparametrized signal PDFs, i.e.:
    - Use mass scales and resolutions
    - Use brem fractions

    Skipping bgauss and cbg, which have two widths

    Parameters
    -----------------
    pdfs             : List of PDF names
    scales_must_float: If true will float scales, false will float original parameters
    '''
    name  = 'reparametrized'
    log.info(f'Testing {name}')

    l_shr = ['mu', 'sg']
    l_flt = []
    d_rep = {'mu' : CorrectionImplementation.scale, 
             'sg' : CorrectionImplementation.reso}

    with ModelFactory.correction(fixed = fix_scales):
        mod = ModelFactory(
            preffix = name,
            obs     = Data.obs,
            l_pdf   = pdfs,
            d_rep   = d_rep,
            l_shared= l_shr,
            l_float = l_flt)
        pdf = mod.get_pdf()

    _check_reparametrized_pdf(
        pdf        = pdf, 
        fix_scales = fix_scales )
#--------------------------
@pytest.mark.parametrize('kind', [Model.cbr, Model.cbl, Model.dscb, Model.gauss, Model.ipatia])
def test_override_parameter(kind: Model):
    '''
    Will create a PDF by overriding parameters
    '''
    log.info(f'Testing {kind}')

    l_shr = ['mu', 'sg']
    l_flt = ['mu']

    MU = 3100
    SG = 20

    ParameterLibrary.print_parameters(kind=kind)
    with ParameterLibrary.values(parameter='mu', kind=kind, val=MU, low=2200, high=3500),\
         ParameterLibrary.values(parameter='sg', kind=kind, val=SG, low=  10, high=  30):

        mod   = ModelFactory(
            preffix = kind,
            obs     = Data.obs,
            l_pdf   = [kind],
            l_shared= l_shr,
            l_float = l_flt)
        pdf   = mod.get_pdf()

    s_par = pdf.get_params()
    [mu]  = [ par for par in s_par if par.name == f'mu_{kind}_flt' ]
    [sg]  = [ par for par in s_par if par.name == f'sg_{kind}'     ]

    assert sg.value().numpy() == SG
    assert mu.value().numpy() == MU 

    print_pdf(pdf)
#--------------------------
def test_shared_parameters():
    '''
    Will create a PDF for each of the models supported
    '''

    l_shr = ['mu', 'sg']
    l_flt = ['mu', 'sg']

    mu = zfit.param.Parameter('mu_flt', 5280, 5000, 5500)
    sg = zfit.param.Parameter('sg_flt',   80,   20,  100)

    mod_1 = ModelFactory(
        preffix = 'cbl',
        obs     = Data.obs,
        l_pdf   = [Model.cbl],
        l_shared= l_shr,
        l_reuse = [mu, sg],
        l_float = l_flt)
    pdf_1 = mod_1.get_pdf()

    mod_2 = ModelFactory(
        preffix = 'cbr',
        obs     = Data.obs,
        l_pdf   = [Model.cbr],
        l_shared= l_shr,
        l_reuse = [mu, sg],
        l_float = l_flt)
    pdf_2 = mod_2.get_pdf()

    print_pdf(pdf_1)
    print_pdf(pdf_2)

    _add_pdfs(l_pdf=[pdf_1, pdf_2])
#--------------------------
def test_from_conf():
    '''
    Test building ModelFactory from configuration
    '''
    obs = zfit.Space('mass', limits=(4500, 7000))

    cfg = ModelFactoryConf.default(pdfs = [Model.gauss])
    obj = ModelFactory.from_conf(
        prefix = 'test', 
        cfg    = cfg,
        obs    = obs)

    pdf = obj.get_pdf()

    assert isinstance(pdf, zpdf)
#--------------------------
