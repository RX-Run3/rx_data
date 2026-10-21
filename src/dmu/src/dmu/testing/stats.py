'''
Module holding functions needed for testing statistical tools
'''

import numpy
import pandas as pnd

from pathlib          import Path
from typing           import overload, Literal, get_args
from dmu.stats        import zfit
from dmu.stats        import Fitter
from dmu.stats        import FitConf
from dmu.stats        import FitResult
from dmu.stats        import print_pdf
from dmu.stats        import save_fit
from dmu.stats        import ZFitPlotter, ZFitPlotterConf
from zfit.pdf         import BasePDF       as zpdf
from zfit.data        import Data          as zdata
from zfit.interface   import ZfitSpace     as zobs
from zfit.param       import Parameter     as zpar
from zfit.loss        import ExtendedUnbinnedNLL, UnbinnedNLL
from dmu              import LogStore

_WEIGHT_NAME  = 'weight'

Loss          = ExtendedUnbinnedNLL | UnbinnedNLL
SingleLiteral = Literal['signal', 'signal_alt', 'signal_kde', 'bkg']
SumLiteral    = Literal['s+b', 's+b+x', 's_alt+b', 'skde+b']
AllLiteral    = Literal['signal', 'signal_alt', 'signal_kde', 'bkg', 's+b', 'skde+b', 's+b+x', 's_alt+b']
SumPDF        = zfit.pdf.SumPDF
Zpdf          = zfit.pdf.BasePDF
xpar          = zfit.param.Parameter | zfit.param.ComposedParameter

log = LogStore.add_logger('rx_testing:stats')
#---------------------------------------------
# Fake/Placeholder fit
#---------------------------------------------
@overload
def get_model(
    kind   : SumLiteral,
    nsig   : zpar| None            = None,
    nsample: int                   = 1000,
    obs    : zobs           | None = None,
    pars   : dict[str,xpar] | None = None,
    suffix : str            | None = None,
    prefix : str            | None = None,
    suffix_pdfs : bool             = False,
    lam    : float                 = -0.0001) -> SumPDF:...
@overload
def get_model(
    kind   : SingleLiteral,
    nsig   : zpar| None            = None,
    nsample: int            | None = None,
    obs    : zobs           | None = None,
    pars   : dict[str,xpar] | None = None,
    suffix : str            | None = None,
    prefix : str            | None = None,
    suffix_pdfs : bool             = False,
    lam    : float                 = -0.0001) -> zpdf:...
def get_model(
    kind   : AllLiteral,
    nsig   : xpar| None            = None,
    nsample: int | None            = None,
    obs    : zobs           | None = None,
    pars   : dict[str,xpar] | None = None,
    suffix : str            | None = None,
    prefix : str            | None = None,
    suffix_pdfs : bool             = False,
    lam    : float                 = -0.0001) -> zpdf | SumPDF:
    '''
    Parameters
    ---------------------
    kind   : 'signal' for Gaussian, 's+b' for Gaussian plus exponential
    nsig   : If passed, will be used to extend signal, in case shared parameters are needed
    pars   : Set of parameters used for reparametrization, by default None
    nsample: Number of entries for normalization of each component, default 1000
    obs    : If provided, will use it, by default None and will be built in function
    suffix : Optional, can be used in case multiple models are needed
    suffix_pdfs: If True, will add suffix to PDF names
    prefix : same as suffix
    lam    : Decay constant of exponential component, set to -0.0001 by default

    Returns
    ---------------------
    zfit PDF for tests
    '''
    if suffix is not None and suffix:
        suffix = suffix.lstrip('_')
        suffix = f'_{suffix}'
    else:
        suffix = ''

    if prefix is not None and prefix:
        prefix = prefix.rstrip('_')
        prefix = f'{prefix}_'
    else:
        prefix = ''

    if obs is None:
        obs  = zfit.Space(f'{prefix}mass{suffix}', limits=(4500, 7000))

    if kind == 'signal_kde':
        return _get_kde_signal(
            suffix_pdfs = suffix_pdfs,
            suffix      = suffix,
            prefix      = prefix,
            nsig        = nsig,
            kind        = kind,
            obs         = obs)

    if kind in ['signal', 'signal_alt']:
        return _get_parametric_signal(
            suffix_pdfs = suffix_pdfs,
            suffix      = suffix,
            prefix      = prefix,
            nsig        = nsig,
            kind        = kind,
            obs         = obs)

    if kind == 'bkg':
        return _get_parametric_background(
            suffix_pdfs = suffix_pdfs,
            suffix      = suffix,
            prefix      = prefix,
            nsample     = nsample,
            lam         = lam,
            obs         = obs)
    # --------------------
    # Section below for composite PDFs with extended components
    # --------------------
    if nsample is None:
        nsample = 1000

    if kind in get_args(SumLiteral):
        return _get_composite_model(
            kind       = kind,
            pars       = pars,
            suffix_pdfs= suffix_pdfs,
            obs        = obs,
            nsample    = nsample,
            suffix     = suffix,
            prefix     = prefix)

    raise NotImplementedError(f'Invalid kind of fit: {kind}')
# ----------------------
def _get_composite_model(
    prefix      : str, 
    suffix      : str, 
    suffix_pdfs : bool,
    kind        : AllLiteral,
    pars        : dict[str,xpar] | None,
    obs         : zobs,
    nsample     : int):
    nbkg = zfit.param.Parameter(f'{prefix}nbkg{suffix}', nsample, 0, 1000_000)
    nsig = _get_signal_yield(
        pars    = pars, 
        suffix  = suffix, 
        prefix  = prefix,
        nsample = nsample)

    models : dict[AllLiteral, AllLiteral] = {
        's+b'     : 'signal', 
        'skde+b'  : 'signal_kde', 
        's+b+x'   : 'signal', 
        's_alt+b' : 'signal_alt'}
    signal_name = models[kind]

    bkg = get_model(
        obs         = obs,
        pars        = pars,
        kind        = 'bkg',
        suffix      = suffix,
        prefix      = prefix,
        suffix_pdfs = suffix_pdfs)

    sig = get_model(
        obs         = obs,
        pars        = pars,
        kind        = signal_name,
        suffix      = suffix,
        prefix      = prefix,
        suffix_pdfs = suffix_pdfs)

    bkg = bkg.create_extended(nbkg)

    if kind == 'skde+b':
        sig.set_yield(nsig)
    else:
        sig = sig.create_extended(nsig)

    if kind in ['s+b', 'skde+b', 's_alt+b']:
        return zfit.pdf.SumPDF([bkg, sig])

    suffix = f'{suffix}_x'
    sig_x = get_model(
        obs         = obs,
        pars        = pars,
        kind        = 'signal_alt',
        suffix      = suffix,
        prefix      = prefix,
        suffix_pdfs = suffix_pdfs)

    nsig = _get_signal_yield(
        pars    = pars, 
        suffix  = suffix, 
        prefix  = prefix,
        nsample = nsample)

    sig_x = sig_x.create_extended(nsig)

    return zfit.pdf.SumPDF([bkg, sig, sig_x])
# ----------------------
def _get_parametric_background(
    obs         : zobs,
    lam         : float,
    nsample     : int | None,
    suffix      : str, 
    prefix      : str,
    suffix_pdfs : bool) -> zpdf:
    pdf_suffix = suffix if suffix_pdfs else ''
    pdf_name   = f'bkg{pdf_suffix}'

    c   = zfit.Parameter(f'{prefix}c{suffix}', lam, -0.01, +0.01)
    pdf = zfit.pdf.Exponential(
        obs  = obs, 
        lam  = c, 
        name = pdf_name)

    if nsample is None:
        return pdf

    nevt = zfit.param.Parameter(f'{prefix}n{pdf_name}', nsample, 0, 1000_000)

    return pdf.create_extended(nevt, name = pdf_name)
# ----------------------
def _get_parametric_signal(
    kind        : str, 
    prefix      : str, 
    suffix      : str, 
    nsig        : xpar | None,
    suffix_pdfs : bool,
    obs         : zobs) -> zpdf:

    pdf_suffix = suffix if suffix_pdfs else ''
    pdf_name   = f'{kind}{pdf_suffix}'

    mu = zfit.Parameter(f'{prefix}mu{suffix}', 5200, 4500, 6000)
    sg = zfit.Parameter(f'{prefix}sg{suffix}',  150,   10, 200)

    pdf : None | zpdf = None
    if kind == 'signal':
        pdf = zfit.pdf.Gauss(
            obs  = obs, 
            mu   = mu, 
            sigma= sg, 
            name = pdf_name)
    elif kind == 'signal_alt':
        ar  = zfit.Parameter(f'{prefix}ar{suffix}', 1,    0,    5)
        al  = zfit.Parameter(f'{prefix}al{suffix}', 1,    0,    5)
        nr  = zfit.Parameter(f'{prefix}nr{suffix}', 1,  -10,  150)
        nl  = zfit.Parameter(f'{prefix}nl{suffix}', 1,  -10,  150)
        pdf = zfit.pdf.DoubleCB(
            mu    = mu, 
            sigma = sg, 
            alphal= al, 
            nl    = nl, 
            alphar= ar, 
            nr    = nr, 
            obs   = obs, 
            name  = pdf_name)
    else:
        raise ValueError(f'Invalid signal type: {kind}')

    if nsig is None:
        return pdf

    nevt = zfit.param.Parameter(f'{prefix}n{pdf_name}', nsig, 0, 1000_000)

    return pdf.create_extended(nevt, name = pdf_name)
# ----------------------
def _get_kde_signal(
    kind        : str, 
    prefix      : str, 
    suffix      : str, 
    nsig        : xpar | None,
    suffix_pdfs : bool,
    obs         : zobs) -> zpdf:

    pdf_suffix = suffix if suffix_pdfs else ''
    pdf_name   = f'{kind}{pdf_suffix}'

    masses = numpy.random.normal(loc = 5280, scale = 150, size = 1000)
    pdf    = zfit.pdf.KDE1DimFFT(
        name = pdf_name,
        data = masses, 
        obs  = obs)

    if nsig is None:
        return pdf

    nevt = zfit.param.Parameter(f'{prefix}n{pdf_name}', nsig, 0, 1000_000)

    pdf.set_yield(nevt)

    return pdf
# ----------------------
def _get_signal_yield(
    pars   : dict[str,xpar] | None,
    nsample: int,
    prefix : str,
    suffix : str) -> xpar:
    '''
    Parameters
    -------------
    pars   : Dictionary storing parameter names and parameters
    nsample: Number of default entries
    suffix : Suffix of paramete(s)

    Returns
    -------------
    Signal yield
    '''
    name = f'{prefix}nsig{suffix}'

    if pars is None:
        return zfit.param.Parameter(name, nsample, 0, 1000_000)

    if name in pars:
        return pars[name]

    return zfit.param.Parameter(name, nsample, 0, 1000_000)
# ----------------------
@overload
def get_nll(
    kind     : SumLiteral,
    pars     : dict[str,xpar] | None = None,
    suffix   : str                   = '_gaus_test_1',
    prefix   : str | None            = None,
    nentries : int                   = 1000) -> ExtendedUnbinnedNLL:...
@overload
def get_nll(
    kind     : SingleLiteral,
    pars     : dict[str,xpar] | None = None,
    suffix   : str                   = '_gaus_test_1',
    prefix   : str | None            = None,
    nentries : int                   = 1000) -> UnbinnedNLL:...
def get_nll(
    kind     : AllLiteral,
    pars     : dict[str,xpar] | None = None,
    suffix   : str                   = '_gaus_test_1',
    prefix   : str | None            = None,
    nentries : int                   = 1000) -> Loss:
    '''
    Parameters
    -------------
    kind    : Type of model, e.g. s+b, signal
    pars    : Dictionary of parameters holding yields, in case they have to be reparametrized
    suffix  : String needed to name parameters
    prefix  : Optional prefix for parameters and models
    nentries: Dataset size

    Returns
    -------------
    Extended NLL from a gaussian plus exponential model
    '''
    # signal and background yield in model are half of
    # requested dataset
    nsample = int(nentries / 2.) 
    pdf     = get_model(
        kind   = kind,
        pars   = pars,
        nsample= nsample,
        prefix = prefix,
        suffix = suffix)

    if kind in get_args(SumLiteral):
        dat = pdf.create_sampler(n=nentries)
        return zfit.loss.ExtendedUnbinnedNLL(model=pdf, data=dat)

    if kind in get_args(SingleLiteral):
        dat = pdf.create_sampler(n=nentries)
        return zfit.loss.UnbinnedNLL(model=pdf, data=dat)

    raise NotImplementedError(f'Invalid kind: {kind}')
#---------------------------------------------
def _pdf_to_data(pdf : zpdf, add_weights : bool) -> zdata:
    numpy.random.seed(42)
    zfit.settings.set_seed(seed=42)

    nentries = 10_000
    data     = pdf.create_sampler(n=nentries)
    if not add_weights:
        return data

    arr_wgt  = numpy.random.normal(loc=1, scale=0.1, size=nentries)
    data     = data.with_weights(arr_wgt)

    return data
#---------------------------------------------
def placeholder_fit(
    kind     : AllLiteral,
    fit_dir  : Path|None,
    df       : pnd.DataFrame|None = None,
    plot_fit : bool               = True) -> FitResult:
    '''
    Function meant to run toy fits that produce output needed as an input
    to develop tools on top of them

    Parameters
    --------------
    kind    : Kind of fit, e.g. s+b for the simples signal plus background fit
    fit_dir : Directory where the output of the fit will go, if None, it won't save anything
    df      : pandas dataframe if passed, will reuse that data, needed to test data caching
    plot_fit: Will plot the fit or not, by default True

    Returns
    --------------
    FitResult object
    '''
    pdf  = get_model(kind)
    if fit_dir is not None:
        print_pdf(pdf, txt_path=f'{fit_dir}/pre_fit.txt')

    if df is None:
        log.warning('Using user provided data')
        data = _pdf_to_data(pdf=pdf, add_weights=True)
    else:
        data = zfit.Data.from_pandas(df, obs=pdf.space, weights=_WEIGHT_NAME)

    if not isinstance(data, zdata):
        raise ValueError('Dataset not unbinned zfit')

    cfg = FitConf.default()
    obj = Fitter(pdf, data)
    res = obj.fit(cfg=cfg)

    if fit_dir is None:
        log.debug('Not saving placeholder fit')
        return res

    log.debug('Saving placeholder fit')
    if plot_fit:
        cfg = ZFitPlotterConf(nbins = 50, stacked = True)
        obj = ZFitPlotter(data=data, model=pdf)
        obj.plot(cfg)

    save_fit(
        data   =data,
        model  =pdf,
        res    =res,
        fit_dir=fit_dir,
        plt_cfg=ZFitPlotterConf.default(),
        d_const={})

    return res
#---------------------------------------------

