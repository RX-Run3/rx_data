'''
Module with utility functions related to the dmu.stats project
'''

import os
import re
import yaml
import numpy
import tempfile
import pandas            as pnd
import matplotlib.pyplot as plt
import tensorflow        as tf

from dmu.pdataframe   import utilities  as put
from zfit             import dill
from dmu              import LogStore, LogLevels
from .imports         import zfit
from typing           import Any, Literal, overload, Final, Sequence
from pathlib          import Path
from contextlib       import contextmanager
from contextvars      import ContextVar

from omegaconf        import OmegaConf, DictConfig
from zfit.data        import Data          as zdata
from zfit.interface   import ZfitSpace     as zobs
from zfit.param       import Parameter     as zpar
from zfit.pdf         import BasePDF       as zpdf
from zfit.result      import FitResult     as zres
from zfit.loss        import ExtendedUnbinnedNLL, UnbinnedNLL

from .fit_result      import FitResult
from .measurement     import Measurement
from .zfit_plotter    import ZFitPlotter, ZFitPlotterConf

log           = LogStore.add_logger('dmu:stats:utilities')
type Loss     = ExtendedUnbinnedNLL | UnbinnedNLL
type SumPDF   = zfit.pdf.SumPDF

AnyKDE   = zfit.pdf.KDE1DimExact | zfit.pdf.KDE1DimFFT | zfit.pdf.KDE1DimISJ

SingleLiteral = Literal['signal', 'signal_alt', 'bkg']
SumLiteral    = Literal['s+b', 's_alt+b']
AllLiteral    = Literal['signal', 'signal_alt', 'bkg', 's+b', 's_alt+b']

_PARS_LINE        : Final[int]            = 9    # Line in postfit.txt where parameters start
_MIN_MERGE_MODELS : Final[int]            = 2    # Cannot merge fewer than 2 models
_MIN_LIMITS       : Final[int]            = 2    # Need at least upper and lower limit in observable
_MIN_INT_PRINT    : Final[int]            = 1000 # Minimum value of a float that would be printed without decimals
_ROOT_DIR         : ContextVar[Path|None] = ContextVar('ROOT_DIR', default = None) # When saving an NLL can override /tmp/ with this directory 
#-------------------------------------------------------
class Data:
    '''
    Data class
    '''
    weight_name = 'weight'
    l_blind_vars= []
# ----------------------
@contextmanager
def blinded_variables(regex_list : list[str]|None = None):
    '''
    Parameters
    -------------
    regex_list: List of regular expressions for variable names to be blinded
    '''
    if regex_list is None:
        raise ValueError('No regex list of variables to blind passed')

    old_val = Data.l_blind_vars
    Data.l_blind_vars = regex_list

    try:
        yield
    finally:
        Data.l_blind_vars = old_val
#-------------------------------------------------------
@contextmanager
def root_directory(root_dir : Path):
    '''
    Parameters
    -------------
    root_dir: Directory that will override /tmp/ when saving NLL
    '''
    root_dir.mkdir(parents = True, exist_ok = True)
    token = _ROOT_DIR.set(root_dir)
    try:
        log.info(f'Overriding root directory in dmu:stats:utilities with: {root_dir}')
        yield
    finally:
        _ROOT_DIR.reset(token)
#-------------------------------------------------------
def name_from_obs(obs : zobs) -> str:
    '''
    Takes zfit observable, returns its name
    It is assumed this is a 1D observable
    '''
    if not isinstance(obs.obs, tuple):
        raise ValueError(f'Cannot retrieve name for: {obs}')

    if len(obs.obs) != 1:
        raise ValueError(f'Observable is not 1D: {obs.obs}')

    return obs.obs[0]
#-------------------------------------------------------
def range_from_obs(obs : zobs) -> tuple[float,float]:
    '''
    Takes zfit observable, returns tuple with two floats, representing range
    '''
    if not isinstance(obs.limits, tuple):
        raise ValueError(f'Cannot retrieve name for: {obs}')

    if len(obs.limits) != _MIN_LIMITS:
        raise ValueError(f'Observable has more than one range: {obs.limits}')

    minx, maxx = obs.limits

    if not isinstance(minx, numpy.ndarray):
        raise ValueError(f'Minx is not an array but: {minx}')

    if not isinstance(maxx, numpy.ndarray):
        raise ValueError(f'Minx is not an array but: {maxx}')

    lower : float = minx[0][0]
    upper : float = maxx[0][0]

    return lower, upper 
#-------------------------------------------------------
def yield_from_zdata(data : zdata) -> float:
    '''
    Parameter
    --------------
    data : Zfit dataset

    Returns
    --------------
    Yield, i.e. number of entries or sum of weights if weighted dataset
    '''

    if data.weights is not None:
        val     = data.weights.numpy().sum()
    else:
        arr_val = data.to_numpy()
        val     = len(arr_val)

    if val < 0:
        raise ValueError(f'Yield cannot be negative, found {val}')

    return val
#-------------------------------------------------------
# Check PDF
#-------------------------------------------------------
def is_pdf_usable(pdf : zpdf) -> bool:
    '''
    Parameters
    ---------------
    pdf: PDF to check

    Returns
    ---------------
    True if PDF is usable
    '''
    minx, maxx = range_from_obs(obs=pdf.space)

    arr_x = numpy.linspace(minx, maxx, 100)
    tf_x  = tf.convert_to_tensor(arr_x)

    try:
        pdf.pdf(tf_x)
    except tf.errors.InvalidArgumentError:
        log.warning('PDF cannot be evaluated')
        return False

    return True
#-------------------------------------------------------
#Zfit/print_pdf
#-------------------------------------------------------
def _get_const(par : zpar , d_const : None | dict[str, tuple[float,float]]) -> str:
    '''
    Takes zfit parameter and dictionary of constraints
    Returns a formatted string with the value of the constraint on that parameter
    '''
    if d_const is None or par.name not in d_const:
        return 'none'

    obj = d_const[par.name]
    if isinstance(obj, (list, tuple)):
        [mu, sg] = obj
        val      = f'{mu:.3e}___{sg:.3e}' # This separator needs to be readable and not a space
    else:
        val      = str(obj)

    return val
#-------------------------------------------------------
def _get_unblinded_vars(
    s_par   : set[zpar], 
    l_blind : list[str]|None = None) -> set[zpar]:
    '''
    Parameters
    -----------------
    s_par  : PDF parameters
    l_blind: List of regular expressions that will be used to select parameters to blind 

    Returns
    -----------------
    set of zfit parameters that should be unblinded
    '''
    s_par_unblinded = set()
    l_blind_regex   = [] if l_blind is None else l_blind

    for par in s_par:
        if _is_par_blinded(name=par.name, l_blind=l_blind_regex):
            continue

        log.debug(f'Blinding {par.name}')
        s_par_unblinded.add(par)

    return s_par_unblinded
# ----------------------
def _is_par_blinded(name : str, l_blind : list[str]) -> bool:
    '''
    Parameters
    -------------
    name   : Name of parameter
    l_blind: List of regular expressions corresponding to parameters to blind

    Returns
    -------------
    True if it is meant to be blinded
    '''
    if len(l_blind) == 0:
        return False

    log.debug(f'Blinding any of: {l_blind}')

    rgx_ors = '|'.join(l_blind)
    regex   = f'({rgx_ors})'

    if re.match(regex, name):
        return True

    return False
#-------------------------------------------------------
def _get_pars(
    pdf   : zpdf,
    blind : None|list[str]) -> tuple[list, list]:
    '''
    Parameters
    ----------------
    pdf  : zfit PDF
    blind: List of regular expressions that match all variables to be blinded, or None in case of no blinding

    Returns
    ----------------
    Tuple with:
    - List of floating(fixed) parameters

    Blinded parameters are removed from this list
    '''
    s_par_flt = pdf.get_params(floating= True)
    s_par_fix = pdf.get_params(floating=False)

    s_par_flt = _get_unblinded_vars(s_par_flt, l_blind=blind)
    s_par_fix = _get_unblinded_vars(s_par_fix, l_blind=blind)

    l_par_flt = list(s_par_flt)
    l_par_fix = list(s_par_fix)

    l_par_flt = sorted(l_par_flt, key=lambda par: par.name)
    l_par_fix = sorted(l_par_fix, key=lambda par: par.name)

    return l_par_flt, l_par_fix
#-------------------------------------------------------
def _get_messages(
    pdf       : zpdf,
    l_par_flt : list[zpar],
    l_par_fix : list[zpar],
    d_const   : None|dict[str,tuple[float,float]] = None) -> list[str]:

    str_space = str(pdf.space)

    l_msg : list[str] = []
    l_msg.append('-' * 20)
    l_msg.append(f'Name : {pdf.name}')
    l_msg.append(f'Label: {pdf.label}')
    l_msg.append(f'TYPE : {type(pdf)}')
    l_msg.append(f'OBS  : {str_space}')
    l_msg.append('-' * 20)
    l_msg.append(f'{"Parameter":<50}{"Value":<15}{"Low":<15}{"High":<15}{"Floating":<10}{"Constraint":<25}')
    l_msg.append('-' * 20)
    for par in l_par_flt:
        value = par.value().numpy()
        low   = par.lower
        hig   = par.upper
        const = _get_const(par, d_const)
        l_msg.append(f'{par.name:<50}{value:<15,.6g}{low:<15,.6g}{hig:<15,.6g}{par.floating:<10}{const:<25}')

    l_msg.append('')

    for par in l_par_fix:
        value = par.value().numpy()
        low   = par.lower
        hig   = par.upper
        const = _get_const(par, d_const)
        l_msg.append(f'{par.name:<50}{value:<15,.6g}{low:<15,.6g}{hig:<15,.6g}{par.floating:<10}{const:<25}')

    return l_msg
#-------------------------------------------------------
def print_pdf(
    pdf      : zpdf,
    d_const  : None|dict[str,tuple[float, float]] = None,
    txt_path : str|None                           = None,
    level    : int                                = LogLevels.info,
    blind    : None|list[str]                     = None) -> list[str]:
    '''
    Function used to print zfit PDFs

    Parameters
    -------------------
    pdf (zfit.PDF): PDF
    d_const (dict): Optional dictionary mapping {par_name : [mu, sg]}
    txt_path (str): Optionally, dump output to text in this path
    level (str)   : Optionally set the level at which the printing happens in screen, default info
    blind (list)  : List of regular expressions matching variable names to blind in printout

    Returns
    -------------------
    List of strings with contents of file to be written.
    Needed for testing
    '''
    blind  = [] if blind is None else blind
    blind += Data.l_blind_vars

    l_par_flt, l_par_fix = _get_pars(pdf, blind)
    l_msg : list[str]    = _get_messages(pdf, l_par_flt, l_par_fix, d_const)
    l_msg               += _print_component_pdfs(pdf = pdf)
    l_msg               += _print_obs(pdf = pdf)

    text = '\n'.join(l_msg)
    text = f'\n{text}'

    if txt_path is not None:
        log.debug(f'Saving to: {txt_path}')
        dir_path = os.path.dirname(txt_path)
        os.makedirs(dir_path, exist_ok=True)
        with open(txt_path, 'w', encoding='utf-8') as ofile:
            ofile.write(text)

        return l_msg

    if   level == LogLevels.error:
        log.error(text)
    elif level == LogLevels.info:
        log.info(text)
    elif level == LogLevels.debug:
        log.debug(text)
    else:
        raise ValueError(f'Invalid level: {level}')

    return l_msg
# ----------------------
def _print_obs(pdf : zpdf) -> list[str]:
    '''
    Parameters
    -------------
    obs: PDF observable

    Returns
    -------------
    List of strings to print
    '''
    val = pdf.space.obs
    if val is None:
        raise ValueError('Observable is None')

    name = val[0]
    obs  = pdf.space
    nrm  = obs if not isinstance(pdf.norm, zfit.Space) else pdf.norm

    lo_ob, up_ob = range_from_obs(obs = obs)  
    lo_no, up_no = range_from_obs(obs = nrm)  

    msg : list[str] = []
    msg.append('---------------------------')
    msg.append('Observable')
    msg.append('---------------------------')
    msg += [f'Name : {name}']
    msg += [f'Obs  : {lo_ob:.0f}; {up_ob:.0f}']
    msg += [f'Norm : {lo_no:.0f}; {up_no:.0f}']

    return msg
# ----------------------
def _print_component_pdfs(pdf : zpdf) -> list[str]:
    '''
    Parameters
    -------------
    pdf: Zfit PDF

    Returns
    -------------
    List of strings with names of composite PDFs, if pdf is a sum
    '''
    if not isinstance(pdf, zfit.pdf.SumPDF):
        log.debug('No component PDFs found')
        return []

    log.debug('Component PDFs found')
    msg = []
    msg.append('---------------------------')
    msg.append('Components')
    msg.append('---------------------------')
    for model in pdf.pdfs:
        msg.append(model.name)

    return msg
#---------------------------------------------
def save_nll(
    loss : Loss, 
    path : Path | None = None) -> Path:
    '''
    Parameters
    -------------
    loss: NLL
    path: Path to file where NLL is saved, by default None, it will be saved to /tmp/

    Returns
    -------------
    Path where it was saved
    '''
    loss_bytes = dill.dumps(loss)
    if path:
        path.parent.mkdir(parents = True, exist_ok = True)
        path.write_bytes(data = loss_bytes)
        return path

    rdir = _ROOT_DIR.get()
    if rdir is not None:
        rdir.mkdir(parents = True, exist_ok = True)

    with tempfile.NamedTemporaryFile(mode='w+b', delete=False, dir = rdir) as temp:
        path = Path(temp.name)
        path.write_bytes(data = loss_bytes)

    return path
#---------------------------------------------
def load_nll(path : Path) -> Loss:
    '''
    Parameters
    --------------
    path: Path to pickle file storing NLL

    Returns
    --------------
    Zfit NLL
    '''
    if not path.exists():
        raise ValueError(f'Path not found: {path}')

    bts = path.read_bytes()
    nll = dill.loads(bts)

    return nll
#---------------------------------------------
@overload
def save_fit(
    data    : zdata,
    model   : None,
    res     : None,
    fit_dir : str|Path,
    plt_cfg : ZFitPlotterConf | None,
    d_const : dict[str,tuple[float,float]]|None = None) -> None: ...
@overload
def save_fit(
    data    : zdata,
    model   : zpdf,
    res     : FitResult,
    fit_dir : str|Path,
    plt_cfg : ZFitPlotterConf | None,
    d_const : dict[str,tuple[float,float]]|None = None) -> Measurement: ...
@overload
def save_fit(
    data    : zdata,
    model   : zpdf | None,
    res     : FitResult | None,
    fit_dir : str|Path,
    plt_cfg : ZFitPlotterConf | None,
    d_const : dict[str,tuple[float,float]]|None = None) -> Measurement | None: ...
def save_fit(
    data    : zdata,
    model   : zpdf|None,
    res     : FitResult | None,
    fit_dir : str|Path,
    plt_cfg : ZFitPlotterConf | None,
    d_const : dict[str,tuple[float,float]]|None = None) -> Measurement | None:
    '''
    Parameters
    --------------------
    data   : Data that was fitted
    model  : PDF to be plotted, if None, will skip steps
    res    : FitResult instance
    fit_dir: Directory where outputs are meant to go
    plt_cfg: Plotting configuration, as taken by ZfitPlotter
    d_const: Dictionary storing constraints

    Returns
    --------------------
    Object holding fitting parameters if fit happened, or None if fit did not run
    '''
    if plt_cfg is None:
        return None

    if isinstance(fit_dir, str):
        fit_dir = Path(fit_dir)

    if data.n_events == 0:
        log.warning('Empty dataset found, not saving fit plot')
        return

    _save_fit_plot(
        data   =data, 
        model  =model, 
        cfg    =plt_cfg, 
        fit_dir=fit_dir)

    pars  = _save_result(
        res      = res, 
        fit_dir  = fit_dir)

    df    = data.to_pandas(weightsname=Data.weight_name)
    opath = f'{fit_dir}/data.json'
    log.debug(f'Saving data to: {opath}')
    df.to_json(opath, indent=2)

    if model is None:
        return None

    print_pdf(model, txt_path=f'{fit_dir}/post_fit.txt', d_const=d_const)
    pdf_to_tex(
        in_path   = Path(f'{fit_dir}/post_fit.txt'),
        out_dir   = Path(fit_dir), 
        d_par     ={'mu' : r'$\mu$'}, 
        skip_fixed=True)

    return pars
# ----------------------
def _save_fit_plot(
    data   : zdata, 
    model  : zpdf|None, 
    fit_dir: Path,
    cfg    : ZFitPlotterConf) -> None:
    '''
    Parameters
    -------------
    data   : Data from fit
    model  : Fitted model
    fit_dir: Directory where plot will go
    cfg    : Config used for plotting
    '''
    fit_dir.mkdir(parents = True, exist_ok = True)

    fit_path_lin = f'{fit_dir}/fit_linear.png'
    fit_path_log = f'{fit_dir}/fit_log.png'

    if model is None:
        log.warning('Model not found, saving dummy plot')
        plt.hist(bins=100, x=data.numpy())
        plt.yscale('linear')
        plt.savefig(fit_path_lin)
        plt.yscale('log')
        plt.savefig(fit_path_log)
        plt.close('all')

        return

    ptr = ZFitPlotter(data=data, model=model)
    ptr.plot(cfg)

    log.info(f'Saving fit to: {fit_path_lin}')
    ptr.set_yscale('linear')
    plt.savefig(fit_path_lin)

    log.info(f'Saving fit to: {fit_path_log}')
    ptr.set_yscale('log')
    plt.savefig(fit_path_log)

    plt.close()
#-------------------------------------------------------
def _save_result(
    fit_dir : Path, 
    res     : FitResult | None) -> None:
    '''
    Saves result as yaml, JSON, pkl

    Parameters
    ---------------
    nentries: Number of entries or sum of weights, if not None 
    fit_dir : Directory where fit result will go
    res     : Fit result object
    '''
    if res is None:
        log.info('No result object found, not saving parameters in pkl or JSON')
        return None

    res.to_json(path = fit_dir / 'parameters.json')
#-------------------------------------------------------
# Make latex table from text file
#-------------------------------------------------------
def _reformat_expo(val : str) -> str:
    regex = r'([\d,\.]+)e([+,\-,\d]+)'
    mtch  = re.match(regex, val)
    if not mtch:
        raise ValueError(f'Cannot extract value and exponent from: {val}')

    [val, exp] = mtch.groups()
    exp        = int(exp)

    return rf'{val}\cdot 10^{{{exp}}}'
#-------------------------------------------------------
def _format_float_str(val : str) -> str:
    '''
    Takes number as string and returns a formatted version
    '''
    val  = val.replace(',', '')
    fval = float(val)
    if abs(fval) > _MIN_INT_PRINT:
        return f'{fval:,.0f}'

    val = f'{fval:.3g}'
    if 'e' in val:
        val = _reformat_expo(val)

    return val
#-------------------------------------------------------
def _info_from_line(line : str) -> tuple|None:
    regex = r'(^\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)'
    mtch  = re.match(regex, line)
    if not mtch:
        return None

    log.debug(f'Reading information from: {line}')

    [par, _, low, high, floating, cons] = mtch.groups()

    try:
        low  = _format_float_str(low)
        high = _format_float_str(high)
    except Exception as exc:
        raise ValueError(f'Cannot extract bounds from: {line}') from exc

    if cons != 'none':
        [mu, sg] = cons.split('___')

        mu   = _format_float_str(mu)
        sg   = _format_float_str(sg)

        cons = rf'$\mu={mu}; \sigma={sg}$'

    return par, low, high, floating, cons
#-------------------------------------------------------
def _df_from_lines(l_line : list[str]) -> pnd.DataFrame:
    df = pnd.DataFrame(columns=['Parameter', 'Low', 'High', 'Floating', 'Constraint'])

    for line in l_line:
        info = _info_from_line(line=line)
        if info is None:
            continue

        par, low, high, floating, cons = info

        df.loc[len(df)] = {
            'Parameter' : par,
            'Low'       : low,
            'High'      : high,
            'Floating'  : floating,
            'Constraint': cons,
            }

    return df
#-------------------------------------------------------
def pdf_to_tex(
    in_path    : Path, 
    out_dir    : Path,
    d_par      : dict[str,str], 
    skip_fixed : bool = True) -> None:
    '''
    Creates a latex table with the same name as `path` but `txt` extension replaced by `tex`

    Parameters
    -----------------
    path : Path to a `txt` file produced by stats/utilities:print_pdf
    d_par: Dictionary mapping parameter names in this file to proper latex names
    '''

    path_str = str(in_path)
    with open(path_str, encoding='utf-8') as ifile:
        l_line = ifile.read().splitlines()
        l_line = l_line[_PARS_LINE:]

    def _rename(name : str) -> str:
        val = d_par.get(name)

        if val is None:
            return name

        return val 

    df = _df_from_lines(l_line)
    df['Parameter']=df.Parameter.apply(_rename)

    out_name = in_path.name.replace('.txt', '.tex')

    if skip_fixed:
        df = df[df.Floating == '1']
        df = df.drop(columns='Floating')

    df_1 = df[df.Constraint == 'none']
    df_2 = df[df.Constraint != 'none']

    df_1 = df_1.sort_values(by='Parameter', ascending=True)
    df_2 = df_2.sort_values(by='Parameter', ascending=True)
    df   = pnd.concat([df_1, df_2])

    put.df_to_tex(df, out_dir / out_name)
#---------------------------------------------
# Zfit utilities 
#---------------------------------------------
def _reformat_values(d_par : dict, fall_back_error : float|None = None) -> dict:
    '''
    Parameters
    --------------
    d_par: Dictionary formatted as:

        {'minuit_hesse': {'cl': 0.6,
                         'error': np.float64(0.04),
                         'weightcorr': <WeightCorr.FALSE: False>},
         'value'       : 0.34},

    fall_back_error: If specified (default None), will pick that value, if error not found

    Returns
    --------------
    Dictionary formatted as:

    {
        'error' : 0.04,
        'value' : 0.34
    }
    '''

    try:
        error : float = d_par['minuit_hesse']['error']
    except KeyError as exc:
        if fall_back_error is not None:
            error = fall_back_error
        else:
            log.error(yaml.dump(d_par))
            raise KeyError('Cannot extract error from parameters') from exc

    error = float(error)

    value : float = d_par['value']

    return {'value' : value, 'error' : error}
#-------------------------------------------------------
def zres_to_cres(
    res             : zres, 
    fall_back_error : float|None = None) -> DictConfig:
    '''
    Parameters
    --------------
    res            : Zfit result object
    fall_back_error: If specified (default None), will pick that value, if error not found

    Returns
    --------------
    OmegaConfig's DictConfig instance
    '''
    # TODO: Needs to be removed once
    # https://github.com/zfit/zfit/issues/702
    # be sorted out
    try:
        res.covariance()
    except Exception as exc:
        raise ValueError('Cannot calculate covariance matrix, result was likely already frozen') from exc

    par = res.params
    try:
        # TODO: Remove ignore once we figure out how to deal properly with typing issues in zfit
        d_par = { par.name : _reformat_values(d_par=d_par, fall_back_error=fall_back_error) for par, d_par in par.items()} # type: ignore
    except KeyError as exc:
        print(res)
        raise KeyError('Fit parameters cannot be used') from exc

    cfg = OmegaConf.create(d_par)

    return cfg
# ----------------------
def to_float(val : Any) -> float:
    '''
    Parameters
    -------------
    val: Object to transform/check into a float 

    Returns
    -------------
    Float version of val, if it can be obtained
    '''
    if not isinstance(val, (float, numpy.floating)):
        raise ValueError(f'Value not floating: {val}')

    return float(val)
# ----------------------
def val_from_zres(
    res  : zres, 
    name : str,
    fall_back : float | None = None) -> float:
    '''
    Parameters
    -------------
    res      : Zfit result, before freezing
    name     : Name of fitting parameter
    fall_back: If parameter not found will raise an error, unless fall back specified

    Returns
    -------------
    Numerical value of fitting parameter
    '''
    for par, data in res.params.items():
        if isinstance(par, zpar) and par.name != name:
            continue

        if isinstance(par, str)  and par      != name:
            continue

        if isinstance(par, zpar):
            return float(par.value().numpy())

        # TODO: Remove ignore when issue be fixed:
        # https://github.com/zfit/zfit/discussions/684#discussioncomment-15376203 
        if isinstance(par,  str):
            val = data['value'] 
            return float(val) # type:ignore

    if fall_back is not None:
        return fall_back

    log.error(res)

    raise ValueError(f'Parameter {name} not found in results')
# ----------------------
def bootstrap_kde[T : zfit.pdf.BasePDF](pdf: T, index: int) -> T:
    """Build one Poisson-bootstrap replica of a 1D zfit KDE from scratch.

    Every event gets an integer weight drawn from Poisson(1), multiplied into
    its original weight (if any). Events that draw zero are dropped. A new KDE
    of the same class is then built on what is left, so the replica's sample
    size fluctuates like a real counting experiment.

    Args:
        pdf: a 1D zfit KDE.
        index: replica index. Used as the random seed, so the same index
            always gives the same replica and different indices give
            different ones.

    Returns:
        The rebuilt KDE.
    """
    if not isinstance(pdf, AnyKDE):
        raise ValueError(f'PDF is not a KDE, but {type(pdf)}')

    values = pdf._data.numpy()  # pyrefly: ignore
    weights= None if pdf._weights is None else pdf._weights.numpy()  # pyrefly: ignore

    rng    = numpy.random.default_rng(index)
    counts = rng.poisson(lam=1.0, size=len(values))

    weights= counts if weights is None else weights * counts

    data = zfit.Data.from_numpy(
        obs    =pdf.space,
        array  =values,
        weights=weights,
    )

    kwargs = {} if isinstance(pdf, zfit.pdf.KDE1DimISJ) else {"bandwidth": float(pdf._bandwidth)}  # pyrefly: ignore
    pdf_bts= type(pdf)(data, obs=pdf.space, **kwargs)
    nevs   = pdf.get_yield()
    if nevs is None:
        return pdf

    pdf_bts.set_yield(nevs)

    return pdf_bts
# ----------------------
def find_model(models : Sequence[zpdf], name : str) -> zpdf:
    '''
    Parameters
    -----------------
    models: List of models, each potentially a sum of models
    name  : Name of model to be found

    Returns
    -----------------
    Found model or will raise value error if not found 
    '''
    for pdf in models:
        if pdf.name == name:
            return pdf

        if not isinstance(pdf, zfit.pdf.SumPDF):
            continue

        try:
            model = find_model(models = pdf.pdfs, name = name)
            return model
        except ValueError:
            continue

    raise ValueError(f'PDF {name} not found')
# ----------------------
def replace_model(
    models : list[zpdf], 
    name   : str,
    pdf    : zpdf) -> list[zpdf]:
    '''
    Parameters
    -----------------
    models: List of models, each potentially a sum of models
    name  : Name of model to be found
    pdf   : PDF to be used as replacement

    Returns
    -----------------
    Input list of PDFs with target replaced
    '''
    for idx, _pdf in enumerate(models):
        if _pdf.name == name:
            models[idx] = pdf
            return models

        if not isinstance(_pdf, zfit.pdf.SumPDF):
            continue

        try:
            pdfs = replace_model(models = _pdf.pdfs, name = name, pdf = pdf)
        except ValueError:
            continue

        models[idx] = zfit.pdf.SumPDF(
            pdfs, 
            fracs = _pdf.fracs, # pyrefly: ignore
            name  = _pdf.name)

        return models

    raise ValueError(f'PDF {name} not found')
#---------------------------------------------
# Mergers
#---------------------------------------------
@overload
def merge_sum_models(
    *,
    obs     : zobs,
    models  : list[zfit.pdf.SumPDF],
    pair    : Literal['by_prefix'],
    prefixes: Sequence[str]) -> zfit.pdf.SumPDF: ...
@overload
def merge_sum_models(
    *,
    obs     : zobs,
    models  : list[zfit.pdf.SumPDF],
    pair    : Literal['by_name', 'by_order'],
    prefixes: None = ...)-> zfit.pdf.SumPDF: ...
def merge_sum_models(
    *,
    obs     : zobs,
    models  : list[zfit.pdf.SumPDF],
    pair    : Literal['by_name', 'by_order', 'by_prefix'],
    prefixes: Sequence[str] | None = None) -> zfit.pdf.SumPDF:
    '''
    Parameters
    --------------
    obs     : Observable needed for full PDF, to specify normalization
    models  : List of models, each representing a full fit model, made of multiple components
    pair    : Criterion used to merge PDFs
    prefixes: List of string

    Returns
    --------------
    Single SumPDF made of components that are the sum of models
    '''
    if prefixes is not None and len(prefixes) == 0:
        raise ValueError('Empty list of prefixes passed')

    nmodel = len(models)
    if nmodel < _MIN_MERGE_MODELS:
        raise ValueError(f'Need at least two models to merge, found: {nmodel}')

    if pair == 'by_prefix':
        if prefixes is None:
            raise ValueError('Prefixes are needed when merging by prefix')

        return _merge_by_prefix(models = models, obs = obs, prefixes = prefixes)

    ncomponents = { len(model.pdfs) for model in models }
    if len(ncomponents) != 1:
        for model in models:
            print_pdf(pdf = model, level = LogLevels.error)

        raise ValueError(f'Models with different sizes found: {ncomponents}')

    if   pair == 'by_name':
        merged_components = _merge_by_name(models = models, obs = obs)
    elif pair == 'by_order':
        merged_components = _merge_by_order(models = models, obs = obs)

    return zfit.pdf.SumPDF(pdfs = merged_components, obs = obs)
#---------------------------------------------
def _merge_by_prefix(
    obs      : zobs, 
    prefixes : Sequence[str],
    models   : list[zfit.pdf.SumPDF]) -> zfit.pdf.SumPDF:
    '''
    Parameters
    --------------
    obs     : Observable needed for full PDF, to specify normalization
    models  : List of models, each representing a full fit model, made of multiple components
    prefixes: Each component of each model starts with one of these prefixes and only one
    Same prefix components get merged

    Returns
    --------------
    Single SumPDF made of components that are the sum of models
    '''
    groups = _group_components(models = models, prefixes = prefixes)

    components : list[zpdf] = []
    for prefix, pdfs in groups.items():
        if len(pdfs) == 1:
            component = pdfs[0]
        else:
            component = zfit.pdf.SumPDF(pdfs = pdfs, obs = obs, name = prefix) 

        components.append(component)

    return zfit.pdf.SumPDF(pdfs = components, obs = obs) 
#---------------------------------------------
def _group_components(
    models   : list[zfit.pdf.SumPDF], 
    prefixes : Sequence[str]) -> dict[str,list[zpdf]]:
    '''
    Group components by prefix, i.e. all components with a given prefix
    would be in same list of PDFs
    '''
    components : list[zpdf] = []
    for model in models:
        components += model.pdfs

    fail = False
    groups : dict[str, list[zpdf]] = {}
    for component in components:
        succeed = False
        for prefix in prefixes:
            if not component.name.startswith(prefix):
                continue

            if prefix in groups:
                groups[prefix].append(component)
            else:
                groups[prefix] = [component]

            succeed = True
            break

        if not succeed:
            log.error(component.name)
            fail = True

    if fail:
        for prefix in prefixes:
            log.error(prefix)

        raise ValueError('Model names found that do not match any prefix')

    return groups
#---------------------------------------------
def _merge_by_name(
    obs    : zobs, 
    models : list[zfit.pdf.SumPDF]) -> list[zfit.pdf.SumPDF]:
    '''
    Parameters
    ----------------
    obs   : Observable needed for full PDF, to specify normalization
    models: List of PDFs, each a sum of components

    Returns
    ----------------
    List of PDFs, each a sum of components
    '''
    components = [ component.name for component in models[0].pdfs ]

    for this_model in models:
        these_components = [ component.name for component in this_model.pdfs ]
        if these_components != components:
            for model in models:
                print_pdf(pdf = model, level = LogLevels.error)

            raise ValueError('Models with different components found')

    merged_components = []
    for name in components:
        pdfs = []
        for model in models:
            [pdf] = [ component for component in model.pdfs if component.name == name ]
        
            pdfs.append(pdf)

        merged_component = zfit.pdf.SumPDF(pdfs = pdfs, obs = obs, name = name)
        merged_components.append(merged_component)

    return merged_components
#---------------------------------------------
def _merge_by_order(
    obs    : zobs, 
    models : list[zfit.pdf.SumPDF]) -> list[zfit.pdf.SumPDF]:
    '''
    Parameters
    ----------------
    obs   : Observable needed for full PDF, to specify normalization
    models: List of PDFs, each a sum of components

    Returns
    ----------------
    List of PDFs, each a sum of components
    '''
    ncomp = len(models[0].pdfs)
    merged_components : list[zfit.pdf.SumPDF] = []
    for icomp in range(ncomp):
        components = [ model.pdfs[icomp] for model in models ]
        merged_component = zfit.pdf.SumPDF(pdfs = components, obs = obs, name = components[0].name)
        merged_components.append(merged_component)

    return merged_components
#---------------------------------------------
