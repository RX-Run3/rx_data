'''
Script needed to calculate smearing factors for q2 distribution
'''

import os
import argparse
import hist
import numpy
import mplhep
import pandas              as pnd
import matplotlib.pyplot   as plt

from functools       import cache
from pathlib         import Path
from typing          import Mapping, Any

from omegaconf       import DictConfig
from ROOT            import RDF
from dmu.stats       import zfit
from zfit.pdf        import BasePDF   as zpdf
from zfit.data       import Data      as zdata
from zfit.result     import FitResult as zres

from dmu             import LogStore
from dmu.rdataframe  import utilities        as rut
from dmu.generic     import utilities        as gut
from dmu.stats       import utilities        as sut
from dmu.stats       import Fitter
from dmu.stats       import ParameterLibrary as PL
from dmu.stats       import ModelFactory
from dmu.stats       import ZFitPlotter
from dmu.stats       import ZFitPlotterConf

from rx_selection    import selection as sel
from rx_common       import Trigger
from rx_data         import RDFGetter
from rx_q2.config    import Config

Parameters=dict[str,tuple[float,float]]
_ARGS : argparse.Namespace | DictConfig | None = None

log=LogStore.add_logger('rx_q2:get_q2_tables')
#-------------------
def _parse_args() -> argparse.Namespace:
    projects = ['rk_ee', 'rkst_ee', 'rk_mm', 'rkst_mm']
    parser = argparse.ArgumentParser(description='Used to produce q2 smearing factors systematic tables')
    parser.add_argument('-v', '--vers' , type =str, help='Version, used for naming of output directory', required=True)
    parser.add_argument('-p', '--proj' , type =str, help='Project', choices=projects                   , required=True)
    parser.add_argument('-y', '--year' , type =str, help='Year'                                        , required=True)
    parser.add_argument('-b', '--brem' , type =str, help='Brem category'                               , required=True)
    parser.add_argument('-k', '--kind' , type =str, help='Kind of sample'                              , required=True)
    parser.add_argument('-B', '--block', type =int, help='Block, by default -1, all'                   , default=-1)
    parser.add_argument('-x', '--syst' , type =str, help='Systematic variabion'                        , default='nom')
    parser.add_argument('-l', '--logl' , type =int, help='Logging level'                               , default=20   )
    parser.add_argument('--skip_fit'   , help='Will not fit, just plot the model'                      , action ='store_true')
    args = parser.parse_args()

    return args
#-------------------
@cache
def _load_config() -> Config:
    args = _parse_args() if _ARGS is None else _ARGS

    vals            = {}
    vals['year']    = args.year
    vals['brem']    = args.brem
    vals['block']   = 'all' if args.block == -1 else str(args.block)
    vals['kind']    = args.kind

    fitting         = {'skip' : args.skip_fit}

    data = gut.load_data(package='rx_q2_data', fpath=f'config/{args.vers}.yaml')
    data['ana_dir'] = os.environ['ANADIR']
    data['vers'   ] = args.vers
    data['syst'   ] = args.syst
    data['logl'   ] = args.logl
    data['project'] = args.proj
    data['input'  ].update(vals)
    data['fitting'].update(fitting)

    zfit.settings.changed_warnings.hesse_name = False

    log.debug('Creating configuration')
    cfg = Config(**data)

    return cfg
#-------------------
def _initialize():
    plt.style.use(mplhep.style.LHCb2)
    cfg = _load_config()

    LogStore.set_level('dmu:stats:fitter'   , cfg.logl)
    LogStore.set_level('dmu:stats:utilities', cfg.logl)
    LogStore.set_level('rx_q2:get_q2_tables', cfg.logl)
    LogStore.set_level('rx_data:rdf_getter' , cfg.logl)
#-------------------
def _get_sig_pdf() -> zpdf:
    cfg = _load_config()
    for pdf_name in cfg.fitting.model.pdfs:
        PL.values(kind=pdf_name, parameter='mu', val=3000, low=2800, high=3300)
        PL.values(kind=pdf_name, parameter='sg', val= 100, low=  10, high= 200)

        if pdf_name == 'cbr':
            PL.values(kind=pdf_name, parameter='nc', val= 3, low= 0.1, high= 10)

        if pdf_name == 'dscb':
            PL.values(kind=pdf_name, parameter='nr', val= 3, low= 0.1, high=128)

    mod     = ModelFactory(
    preffix = 'q2_smearing',
    obs     = cfg.obs,
    l_pdf   = cfg.fitting.model.pdfs,
    l_shared= ['mu', 'sg'],
    l_float = ['mu', 'sg'])
    pdf     = mod.get_pdf()

    return pdf
#-------------------
@cache
def _get_full_pdf() -> zpdf:
    cfg = _load_config()
    sig = _get_sig_pdf()
    nsg = zfit.Parameter('nsg', 10_000, 100, 2_000_000)
    sig = sig.create_extended(nsg, name='Signal')

    if cfg.input.kind == 'sim':
        return sig

    bkg = _get_bkg_pdf()
    pdf = zfit.pdf.SumPDF([bkg, sig])

    return pdf
#-------------------
def _get_bkg_pdf() -> zpdf:
    cfg = _load_config()
    lam = zfit.Parameter('lam', 0.0, -0.01, 0)
    bkg = zfit.pdf.Exponential(lam=lam, obs=cfg.obs, name='')

    nbk = zfit.Parameter('nbk', 10, 1, 100_000)
    bkg = bkg.create_extended(nbk, name='Combinatorial')

    return bkg
#-------------------
def _fix_pdf(pdf : zpdf, d_fix : Parameters | None) -> zpdf:
    '''
    This will take a PDF and a dictionary of paramters
    It will fix the PDF parameters according to dictionary
    '''
    if d_fix is None:
        return pdf

    l_par = list(pdf.get_params(floating=True))

    log.info('-----------------')
    log.info('Fixing parameters')
    log.info('-----------------')
    for par in l_par:
        if par.name not in d_fix:
            log.info(f'{par.name:<20}{"->":<10}{"floating":>20}')
            continue

        fix_val, _ = d_fix[par.name]
        par.set_value(fix_val)
        par.floating=False

        log.info(f'{par.name:<20}{"->":<10}{fix_val:>20.3e}')

    return pdf
#-------------------
def _get_pdf(kind : str) -> zpdf:
    if kind == 'sim':
        return _get_sig_pdf()

    if kind == 'dat':
        return _get_full_pdf()

    raise NotImplementedError(f'Cannot get PDF for: {kind}')
#-------------------
def _par_val_from_dict(d_par : Mapping[str, Mapping[str,Any]]) -> tuple[float,float]:
    value = d_par['value']
    if not isinstance(value, float):
        raise TypeError(f'Value is not a float but {value}, result was likely not frozen')

    if 'hesse' not in d_par:
        return value, -1

    error = d_par['hesse']['error']
    if not isinstance(error, float):
        raise TypeError(f'Expected a float as the error, got: {error}')

    return value, error
#-------------------
def _get_pars(res : zres) -> Parameters:
    '''
    Parameters
    -------------------
    res: Fit result after freezing

    Returns
    -------------------
    Dictionary with:

    Key  : Parameter name
    Value: Tuple with value and error
    '''
    d_par = dict()
    for par, d_val in res.params.items():
        name = par.name
        if not isinstance(name, str):
            raise ValueError(f'Parameter name not a string, but: {name}')

        d_par[name] = _par_val_from_dict(d_val)

    return d_par
#-------------------
def _fit(d_fix : Parameters | None = None)-> Parameters | None:
    cfg = _load_config()
    kind= cfg.input.kind
    pdf = _get_pdf(kind)
    dat = _get_data(pdf, kind)
    pdf = _fix_pdf(pdf, d_fix)

    obj = Fitter(pdf=pdf, data=dat)

    if cfg.fitting.skip:
        log.warning('Skipping fit')
        return None

    res=obj.fit(cfg=cfg.fitting[kind].model_dump())

    if res is None:
        _plot_fit(dat, pdf, res)

        log.info(res)
        raise ValueError('Fit failed')

    if res.status != 0:
        _plot_fit(dat, pdf, res)

        log.info(res)
        raise ValueError(f'Finished with status/validity: {res.status}/{res.valid}')

    log.info(30 * '-')
    log.info('Found parameters:')
    log.info(30 * '-')
    log.info(res)
    log.info(30 * '-')
    _plot_fit(dat, pdf, res)

    d_par = _get_pars(res)

    sut.save_fit(data=dat, model=pdf, res=res, fit_dir=cfg.out_dir, plt_cfg=cfg.plots.model_dump())

    return d_par
#-------------------
def _get_data(pdf : zpdf, kind : str) -> zdata:
    cfg       = _load_config()
    data_path = cfg.out_dir / '.data.parquet'
    if data_path.exists():
        log.warning(f'Data found, loading from: {data_path}')
        df  = pnd.read_parquet(data_path)
        # TODO: Here the weights need to be put back, once the bug in zfit be fixed
        dat = zfit.data.Data.from_pandas(df, obs=cfg.obs)
        if not isinstance(dat, zdata):
            str_type = str(type(dat))
            raise ValueError(f'Data is of the wrong type: {str_type}')

        return dat

    rdf     = _get_rdf(kind=kind)
    d_data  = rdf.AsNumpy([cfg.fitting.mass, cfg.fitting.weights])
    df      = pnd.DataFrame(d_data)
    df.to_parquet(data_path) # Caching now will avoid redoing this if fit fails

    obs     = pdf.space
    # TODO: Here the weights need to be put back, once the bug in zfit be fixed
    dat     = zfit.Data.from_pandas(obs=obs, df=df)
    if not isinstance(dat, zdata):
        str_type = str(type(dat))
        raise ValueError(f'Data is of the wrong type: {str_type}')

    _plot_data(df)

    return dat
#-------------------
def _plot_data(df : pnd.DataFrame) -> None:
    '''
    Parameters
    --------------
    df  : DataFrame with fitted data
    '''
    cfg     = _load_config()
    arr_mas = df[cfg.fitting.mass   ].to_numpy()
    arr_wgt = df[cfg.fitting.weights].to_numpy()

    [[lower]], [[upper]] = cfg.obs.limits
    _, ax     = plt.subplots(figsize=(15, 10))
    data_hist = hist.Hist.new.Regular(
        cfg.plots.nbins,
        lower,
        upper,
        name     ='',
        underflow=False,
        overflow =False)
    data_hist = data_hist.Weight()
    data_hist.fill(arr_mas, weight=arr_wgt)

    mplhep.histplot(
        data_hist,
        yerr    = True,
        color   = 'black',
        histtype= 'errorbar',
        ax      = ax
    )

    title=f'Entries={arr_wgt.size:.0f}; Sum={numpy.sum(arr_wgt):.0f}'

    plt_path = cfg.out_dir / 'unfitted_dataset.png'

    log.info(f'Saving to: {plt_path}')
    plt.title(title)
    plt.savefig(plt_path)
    plt.close('all')
#-------------------
def _add_q2_region_lines(obj : ZFitPlotter) -> None:
    axis = obj.axs[0]
    axis.axvline(x=2450, c='red', ls=':')
    axis.axvline(x=3600, c='red', ls=':')
#-------------------
def _get_text(data : zdata) -> tuple[str,str]:
    nentries= data.num_entries.numpy()
    text    = f'Candidates={nentries}'
    l_part  = []
    cfg     = _load_config()

    for name, value in cfg.input.selection.items():
        l_part.append(f'{name}: {value}')

    title = '; '.join(l_part)

    return text, title
#-------------------
def _plot_fit(
    dat        : zdata,
    pdf        : zpdf,
    res        : zres) -> None:
    '''
    Function in charge of plotting fit from data and model
    '''
    cfg = _load_config()
    obj = ZFitPlotter(data=dat, model=pdf, result=res)
    for yscale in ['log', 'linear']:
        for add_pars in ['pars', 'no_pars']:
            pars  = None if add_pars == 'no_pars' else 'all'
            text, title = _get_text(data = dat)

            cfg_plt = ZFitPlotterConf(
                nbins     = cfg.plots.nbins,
                d_leg     = cfg.plots.d_leg,
                plot_range= cfg.obs_range,
                yscale    = yscale,
                ext_text  = text,
                add_pars  = pars)
            obj.plot(cfg_plt)

            _add_q2_region_lines(obj)

            obj.axs[0].set_title(title)
            obj.axs[0].axhline(y=0, c='gray')

            plot_path = cfg.out_dir / f'{add_pars}_{yscale}.png'
            log.info(f'Saving to: {plot_path}')
            plt.savefig(plot_path)
            plt.close()
#-------------------
def _get_rdf(kind : str) -> RDF.RNode:
    log.info(f'Getting data for: {kind}')

    cfg    = _load_config()
    inp    = cfg.input
    sample = inp.samples[cfg.project][kind]
    trigger= inp.trigger[cfg.project]
    with RDFGetter.exclude_friends(names=inp.friends['excluded']):
        gtr    = RDFGetter(sample=sample, trigger=Trigger(trigger))
        rdf    = gtr.get_rdf(per_file=False)

    trigger= cfg.input.trigger[cfg.project]

    d_sel = sel.selection(trigger=trigger, q2bin='jpsi', process=sample)

    for cut_name, cut_value in d_sel.items():
        log.debug(f'{cut_name:<20}{cut_value}')
        rdf = rdf.Filter(cut_value, cut_name)

    rep = rdf.Report()
    if log.getEffectiveLevel() == 10:
        rep.Print()

    _save_cutflow(rep=rep, cuts=d_sel)

    return rdf
# ----------------------
def _save_cutflow(rep : RDF.RCutFlowReport , cuts : dict[str,str]) -> None:
    '''
    Parameters
    -------------
    rep : Cutflow report
    cuts: Dictionary with cuts
    kind: dat or sim
    '''
    cfg = _load_config()
    df  = rut.rdf_report_to_df(rep)

    df.to_markdown(cfg.out_dir / 'cutflow.md')
    gut.dump_json(data=cuts, path=cfg.out_dir / 'selection.yaml', exists_ok=True)
#-------------------
def _make_table():
    cfg = _load_config()
    if cfg.input.kind == 'sim':
        log.info('Running simulation fit')
        _fit(d_fix=None)
        return

    log.info('Running data fit')
    dat_par_path   = cfg.out_dir / 'parameters.json'
    sim_par_path   = Path(str(dat_par_path).replace('/dat/', '/sim/'))

    d_sim_par      = gut.load_json(sim_par_path)
    d_fix_par      = { key : val for key, val in d_sim_par.items() if ('mu' not in key) and ('sg' not in key) }

    _fit(d_fix=d_fix_par)
#-------------------
#-------------------
def main(args : DictConfig | None = None):
    '''
    Entry point
    '''
    global _ARGS
    _ARGS = args
    _initialize()

    cfg = _load_config()
    with sel.custom_selection(d_sel = cfg.input.selection):
        _make_table()
#-------------------
if __name__ == '__main__':
    main()
