from ._bufferdict import BUFFERDICTDATA as BUFFERDICTDATA, add_parameter_parentheses as add_parameter_parentheses, dictkey as dictkey, get_dictkeys as get_dictkeys, has_dictkey as has_dictkey, nonredundant_keys as nonredundant_keys, trim_redundant_keys as trim_redundant_keys
from ._gvarcore import arccos as arccos, arccosh as arccosh, arcsin as arcsin, arcsinh as arcsinh, arctan as arctan, arctan2 as arctan2, arctanh as arctanh, cos as cos, cosh as cosh, exp as exp, fabs as fabs, gvar_function as gvar_function, log as log, msum_gvar as msum_gvar, sin as sin, sinh as sinh, sqrt as sqrt, square as square, tan as tan, tanh as tanh, wsum_der as wsum_der, wsum_gvar as wsum_gvar
from ._svec_smat import smask as smask, smat as smat, svec as svec
from ._utilities import GVarRef as GVarRef, bootstrap_iter as bootstrap_iter, collect_gvars as collect_gvars, corr as corr, correlate as correlate, dependencies as dependencies, deriv as deriv, disassemble as disassemble, distribute_gvars as distribute_gvars, dump as dump, evalcorr as evalcorr, evalcov_blocks as evalcov_blocks, evalcov_blocks_dense as evalcov_blocks_dense, filter as filter, fmt_errorbudget, fmt_values as fmt_values, gammaP as gammaP, gdump as gdump, gdumps as gdumps, gload as gload, gloads as gloads, gvar_from_sample as gvar_from_sample, is_primary as is_primary, load as load, missing_dependencies as missing_dependencies, reassemble as reassemble, rebuild as rebuild, remove_gvars as remove_gvars, uncorrelated as uncorrelated, valder as valder
from _typeshed import Incomplete
from collections.abc import Generator
from gvar import cspline as cspline, dataset as dataset, linalg as linalg, ode as ode, pade as pade, powerseries as powerseries, root as root
from typing import NamedTuple

__version__: str
gvar: Incomplete
RNG: Incomplete

def ranseed(seed=None, size: int = 3, version=None): ...
def switch_gvar(cov=None): ...
def restore_gvar(): ...
def gvar_factory(cov=None): ...
def qqplot(g1, g2=None, plot=None, eps=None, svdcut=None, dof=None, nocorr: bool = False): ...
def chi2(g1, g2=None, eps=None, svdcut=None, dof=None, nocorr: bool = False): ...
def equivalent(g1, g2, rtol: float = 1e-10, atol: float = 1e-10): ...
def fmt_chi2(f): ...
def tabulate(g, ncol: int = 1, headers: bool = True, offset: str = '', ndecimal=None, keys=None): ...

class PDF:
    nblocks: Incomplete
    svdcut: Incomplete
    eps: Incomplete
    mode: Incomplete
    fcntype: Incomplete
    i_wgts: Incomplete
    i_invwgts: Incomplete
    logdet: Incomplete
    dp_dchiv: Incomplete
    size: Incomplete
    shape: Incomplete
    mean: Incomplete
    meanflat: Incomplete
    nmod: int
    correction: int
    distribution: Incomplete
    nchiv: Incomplete
    lognorm: Incomplete
    def __init__(self, g, svdcut: float = 1e-12, eps=None, noise: bool = False, mode=None, decorrelate: bool = False) -> None: ...
    cov: Incomplete
    invcov: Incomplete
    def chiv(self, p=None, pflat=None, mode: str = 'default'): ...
    def pflat(self, chiv, mode: str = 'default'): ...
    def chi2(self, p, mode: str = 'default'): ...
    def logpdf(self, p, mode: str = 'default'): ...
    def __call__(self, p, mode: str = 'default'): ...
    def sample(self, nbatch=None, uniform=None, mode: str = 'default'): ...

class oldPDF:
    vec_sig: Incomplete
    vec_isig: Incomplete
    sig: Incomplete
    dpdx: Incomplete
    meanflat: Incomplete
    size: Incomplete
    shape: Incomplete
    mean: Incomplete
    sample: Incomplete
    log_gnorm: Incomplete
    def __init__(self, g, svdcut: float = 1e-12) -> None: ...
    def x2dpflat(self, x, mode=None): ...
    def dpflat2x(self, dpflat, mode=None): ...
    def p2x(self, p, mode=None): ...
    def logpdf(self, p, mode=None): ...
    def __call__(self, p, mode=None): ...

class PDFHistogram:

    class Histogram(NamedTuple):
        bins: Incomplete
        prob: Incomplete
        stats: Incomplete
        norm: Incomplete
    default_nbin: int
    default_binwidth: float
    bins: Incomplete
    midpoints: Incomplete
    widths: Incomplete
    g: Incomplete
    nbin: Incomplete
    def __init__(self, g=None, nbin=None, binwidth=None, bins=None) -> None: ...
    def count(self, data): ...
    def analyze(self, count): ...
    @staticmethod
    def gaussian_pdf(x, g): ...
    def make_plot(self, count, plot=None, show: bool = False, plottype: str = 'probability', bar=..., errorbar=..., gaussian=...): ...

class _TwoSided:
    loc: Incomplete
    plus: Incomplete
    minus: Incomplete
    type: Incomplete
    def __init__(self, loc, plus, minus, type: str = 'splitnormal') -> None: ...
    def __call__(self, x): ...

class PDFStatistics:
    prefix: Incomplete
    bins: Incomplete
    prob: Incomplete
    splitnormal: Incomplete
    median: Incomplete
    mean: Incomplete
    sdev: Incomplete
    skew: Incomplete
    ex_kurt: Incomplete
    gvar: Incomplete
    def __init__(self, moments=None, histogram=None, prefix: str = '   ') -> None: ...
    def plot_histogram(self, plot=None, show: bool = False, fits=['mean', 'split-normal', 'median'], errorbars: bool = True): ...

def make_fake_data(g, fac: float = 1.0): ...
def make_fake_sample_iter(g, n, fac: float = 1.0) -> Generator[Incomplete]: ...
fmt_partialsdev = fmt_errorbudget
