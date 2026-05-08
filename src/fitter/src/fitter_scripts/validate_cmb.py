'''
Script used to validate PDFs needed to fit combinatorial
'''
import os
import argparse
import pandas   as pnd

from contextlib   import ExitStack
from functools    import cache
from typing       import Final
from ROOT         import RDF # type: ignore
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import ZFitPlotterConf
from dmu.generic  import utilities as gut
from dmu.plotting import BandPlotter, BandPlotterConf
from rx_selection import selection as sel
from rx_common    import Mass, Project, Qsq, Component, Trigger
from rx_data      import RDFGetter
from fitter       import FitSummary
from fitter       import CmbValidationConfig
from fitter       import CmbValidatorConf
from fitter       import CmbInputConfig
from fitter       import CmbValidator
from fitter       import CmbOutputConfig
from fitter       import MVAWp

log=LogStore.add_logger('rx_fitter:validate_cmb')
_IHEP_ANADIR        : Final[str] = '/publicfs/ucas/user/campoverde/Data'
_CMB_SUFFIX         : Final[str] = '_cmb_1' # end part of string in combinatorial fits parameters
_OS_DROPPED_COLUMNS : Final[list[str]] = ['q2bin', 'channel', 'brem', 'mva_prc', 'project', 'block', 'component']
_SIGNAL_PREFIX      : Final[str] = 'yld_bpkpee' 
# ----------------------
def _get_conf() -> CmbValidatorConf:
    parser = argparse.ArgumentParser(description='Used to perform fits to validate choice of PDF for combinatorial')
    parser.add_argument('-c', '--cutflow', type=       str, help='Cutflow name')
    parser.add_argument('-q', '--q2bin'  , type=       Qsq, help='Q2bin'          , choices =     Qsq)
    parser.add_argument('-M', '--mass'   , type=      Mass, help='Mass to fit'    , choices =    Mass)
    parser.add_argument('-t', '--trigger', type=   Trigger, help='Name of trigger', choices = Trigger)
    parser.add_argument('-s', '--sample' , type= Component, help='Name of sample' , default = Component.data_24)
    args = parser.parse_args()

    data = {
        'q2bin'  : args.q2bin,
        'mass'   : args.mass,
        'trigger': args.trigger,
        'sample' : args.sample,
        'cutflow': args.cutflow,
    }

    ana_dir    = Path(os.environ['ANADIR'])

    input      = CmbInputConfig(**data)
    validation = CmbValidationConfig.from_file(fname = f'combinatorial/config_{args.q2bin}.yaml') 

    cfg_plt    = ZFitPlotterConf.default()
    cfg_plt    = cfg_plt.model_copy(update = {'nbins' : 30})

    output     = CmbOutputConfig(
        plots    = cfg_plt,
        dir_path = ana_dir / 'combinatorial/validation'
    )

    return CmbValidatorConf(
        input      = input,
        output     = output,
        validation = validation)
# ----------------------
@cache
def _get_rdf(cfg : CmbValidatorConf) -> RDF.RNode:
    gtr = RDFGetter(
        trigger= cfg.input.trigger,
        sample = cfg.input.sample)
    rdf = gtr.get_rdf(per_file = False)

    with sel.custom_selection(d_sel = cfg.validation.selection):
        rdf = sel.apply_full_selection(
            rdf     = rdf,
            out_path= cfg.out_dir,
            q2bin   = cfg.input.q2bin,
            process = cfg.input.sample,
            trigger = cfg.input.trigger)

    return rdf
# ----------------------
def _get_pars(
    label : str,
    cut   : str,
    cfg   : CmbValidatorConf) -> pnd.DataFrame:
    '''
    Parameters
    -----------------
    label: Label of dataset
    cut  : Cut associated to working point 
    cfg  : Config needed to validate

    Returns
    -----------------
    dataframe with parameters
    '''
    out_path = cfg.out_dir / f'{label}/parameters.parquet'

    if out_path.exists():
        log.info(f'Parameters found from cache, loading: {out_path}')
        return pnd.read_parquet(path = out_path)

    log.info(f'Parameters not found from cache: {out_path}')

    rdf = _get_rdf(cfg = cfg)
    rdf = rdf.Filter(cut, label)

    obj = CmbValidator(
        rdf = rdf,
        cfg = cfg)
    res = obj.run(label = label)

    log.info(f'Caching to: {out_path}')
    res.df.to_parquet(path = out_path)

    return res.df
# --------------------------------
def _plot(
    cfg_val : CmbValidatorConf,
    df      : pnd.DataFrame) -> None:
    '''
    Parameters
    -------------------
    df     : Dataframe with values of parameters and errors
    cfg_val: Config used for combinatorial validation
    '''
    data= gut.load_data(
        package = 'fitter_data', 
        fpath   = f'combinatorial/plots_{cfg_val.input.q2bin}.yaml')
    data['out_dir'] = str(cfg_val.out_dir)

    cfg = BandPlotterConf(**data)
    ptr = BandPlotter(cfg = cfg, df = df)
    ptr.plot()
# --------------------------------
def _get_renaming(
    prefixes : set[str],
    df       : pnd.DataFrame):

    renaming : dict[str,str] = {}
    parameters = df['Parameter'].to_list()
    for parameter in parameters:
        if parameter.startswith(_SIGNAL_PREFIX):
            renaming[parameter] = 'nev' 
            continue

        if not any(parameter.startswith(pref) for pref in prefixes):
            continue

        suffix   = '' if parameter == 'pvalue' else _CMB_SUFFIX
        [target] = [ f'{prefix}{suffix}' for prefix in prefixes if parameter.startswith(prefix) ]

        renaming[parameter] = target

    return renaming
# --------------------------------
def _preprocess_os_df(
    df       : pnd.DataFrame,
    cfg      : CmbValidatorConf,
    prefixes : set[str]) -> pnd.DataFrame:
    '''
    Parameters
    ------------
    df       : DataFrame from OS fits
    prefixes : Prefixes of parameters, e.g. ap_hypexp

    Returns
    ------------
    DataFrame with columns: Parameter, Value, Error, Fit, Category
    '''
    df = df.query(f'q2bin == \"{cfg.input.q2bin}\"')
    df = df.drop(columns = _OS_DROPPED_COLUMNS)
    df = df.rename(
        columns = {'mva_cmb' : 'Fit'},
        inplace = False)

    df['Category']  = 'OS'
    vars_dict       = _get_renaming(prefixes = prefixes, df = df)
    pars            = df['Parameter']
    flags           = pars.isin(vars_dict)
    df              = df[flags]
    df['Parameter'] = df['Parameter'].map(vars_dict)
    df              = df.sort_values(by = ['Fit', 'Parameter'])
    df              = df.reset_index(drop = True)

    return df
# --------------------------------
def _get_ss_df(cfg : CmbValidatorConf) -> list[pnd.DataFrame]:
    '''
    Parameters
    ------------------
    cfg: Config object needed to run SS parameter extraction

    Returns
    ------------------
    Dataframes with parameters for SS fits
    '''
    l_df : list[pnd.DataFrame] = []
    categories : dict[str,str] = {'Both': '(1)'}
    if cfg.input.trigger.project == Project.rk:
        categories['+++'] = 'TMath::Abs(total_charge) == 3'
        categories['+--'] = 'TMath::Abs(total_charge) == 1'

    for label, cut in categories.items():
        df  = _get_pars(
            label = label,
            cut   = cut,
            cfg   = cfg)

        df['Category'] = 'SS' if label == 'Both' else label
        l_df.append(df)

    return l_df
# --------------------------------
def _get_prefix(param : str) -> str:
    parts  = param.split('_')
    parts  = parts[:2]
    prefix = '_'.join(parts)

    return prefix
# --------------------------------
def main():
    '''
    Entry point
    '''
    cfg  = _get_conf()
    l_df = _get_ss_df(cfg = cfg)
    pars = l_df[0]['Parameter'].to_list()
    prefixes = { _get_prefix(param = par) for par in pars }

    with ExitStack() as stack:
        stack.enter_context(gut.environment(mapping = {'ANADIR' : _IHEP_ANADIR}))
        stack.enter_context(MVAWp.mult_factor(value = 100))

        smr= FitSummary(
            name   = 'rare_fix_cmb_pars',
            data   = Component.data_24,
            signal = None)
        df = smr.get_df(
            by_fit       = False,
            force_update = True)

        df = _preprocess_os_df(
            df       = df,
            cfg      = cfg,
            prefixes = prefixes)

        l_df.append(df)

    df = pnd.concat(l_df, ignore_index=True)
    _plot(df = df, cfg_val = cfg)
# --------------------------------
if __name__ == '__main__':
    main()
