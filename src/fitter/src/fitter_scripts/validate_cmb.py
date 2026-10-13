'''
Script used to validate PDFs needed to fit combinatorial
'''
import os
import argparse
import pandas   as pnd

from contextlib   import ExitStack
from typing       import Final
from ROOT         import RDF # type: ignore
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import ZFitPlotterConf
from dmu.generic  import utilities as gut
from dmu.plotting import BandPlotter, BandPlotterConf
from rx_selection import selection as sel
from rx_common    import Mass, Qsq, Component, Trigger
from rx_data      import RDFGetter
from fitter       import FitSummary
from fitter       import CmbValidationConfig
from fitter       import CmbValidatorConf
from fitter       import CmbInputConfig
from fitter       import CmbValidator
from fitter       import CmbOutputConfig

log=LogStore.add_logger('rx_fitter:validate_cmb')
_IHEP_ANADIR        : Final[str] = '/publicfs/ucas/user/campoverde/Data'
_CMB_SUFFIX         : Final[str] = '_cmb_1' # end part of string in combinatorial fits parameters
_OS_DROPPED_COLUMNS : Final[list[str]] = ['q2bin', 'channel', 'brem', 'mva_prc', 'project', 'block', 'component']
_CMB_PREFIX         : Final[str] = 'yld_comb' 
# ----------------------
def _get_conf() -> CmbValidatorConf:
    parser = argparse.ArgumentParser(description='Used to perform fits to validate choice of PDF for combinatorial')
    parser.add_argument('-c', '--cutflow', type=     str, help='Cutflow name')
    parser.add_argument('-q', '--q2bin'  , type=     Qsq, help='Q2bin'          , choices =     Qsq)
    parser.add_argument('-M', '--mass'   , type=    Mass, help='Mass to fit'    , choices =    Mass)
    parser.add_argument('-t', '--trigger', type= Trigger, help='Name of trigger', choices = Trigger)
    args = parser.parse_args()

    samples : list[Component] = [
        Component.data_24,
        Component.bpkpee, 
    ]

    ana_dir  = Path(os.environ['ANADIR'])
    cfg_input= CmbInputConfig(
        cutflow = args.cutflow,
        samples = samples,
        trigger = args.trigger,
        mass    = args.mass,
        q2bin   = args.q2bin)

    validation = CmbValidationConfig.from_file(fname = f'combinatorial/config_{args.q2bin}.yaml')

    cfg_plt    = ZFitPlotterConf.default()
    cfg_plt    = cfg_plt.model_copy(update = {'nbins' : 30})

    output     = CmbOutputConfig(
        plots    = cfg_plt,
        dir_path = ana_dir / 'combinatorial/validation'
    )

    return CmbValidatorConf(
        input      = cfg_input,
        output     = output,
        validation = validation)
# ----------------------
def _get_rdfs(
    cfg : CmbValidatorConf, 
    cut : str) -> dict[Component, RDF.RNode]:
    '''
    Parameters
    --------------
    cfg: Config object
    cut: Selection used to define label, e.g. +++, +--

    Returns
    --------------
    Tuple with dataframes with data and MC after full selection
    '''
    rdfs : dict[Component, RDF.RNode] = {}
    for sample in cfg.input.samples:
        gtr = RDFGetter(
            trigger = cfg.input.trigger,
            sample  = sample)
        rdf = gtr.get_rdf(per_file = False)

        with sel.custom_selection(d_sel = cfg.validation.selection):
            rdf = sel.apply_full_selection(
                rdf     = rdf,
                out_path= cfg.out_dir(sample),
                q2bin   = cfg.input.q2bin,
                process = sample,
                trigger = cfg.input.trigger)

        rdf = rdf.Filter(cut)
        rdfs[sample] = rdf

    return rdfs 
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
    parquet_path = cfg.out_dir(component = Component.data_24) / f'{label}/parameters.parquet'

    if parquet_path.exists():
        log.info(f'Parameters found from cache, loading: {parquet_path}')
        return pnd.read_parquet(path = parquet_path)

    log.info(f'Parameters not found from cache: {parquet_path}')

    rdfs = _get_rdfs(cfg = cfg, cut = cut)

    obj = CmbValidator(
        rdfs = rdfs,
        cfg  = cfg)
    res = obj.run(label = label)

    log.info(f'Caching to: {parquet_path}')
    res.df.to_parquet(path = parquet_path)

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
    data['out_dir'] = str(cfg_val.out_dir(component = Component.data_24))

    cfg = BandPlotterConf(**data)
    ptr = BandPlotter(cfg = cfg, df = df)
    ptr.plot()
# --------------------------------
def _get_renaming(
    prefixes : set[str],
    df       : pnd.DataFrame) -> dict[str,str]:
    '''
    Parameters
    -------------
    prefixes: Strings used to find parameter columns 
    df      : Dataframe with OS fits parameters

    Returns
    -------------
    Dictionary mapping old (from OS fits) to new (from SS fits) names
    '''
    renaming : dict[str,str] = {}
    parameters = df['Parameter'].to_list()
    for parameter in parameters:
        if parameter.startswith(_CMB_PREFIX):
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
def _get_os_df(
    df_ss : pnd.DataFrame, 
    cfg   : CmbValidatorConf) -> list[pnd.DataFrame]:
    '''
    Parameters
    --------------
    df_ss : Dataframe with parameters from SS fit
    cfg   : Configuration object

    Returns
    --------------
    List of dataframes with parameters from OS fits
    '''
    pars     = df_ss['Parameter'].to_list()
    prefixes = { _get_prefix(param = par) for par in pars }
    l_df : list[pnd.DataFrame] = []

    with ExitStack() as stack:
        stack.enter_context(gut.environment(mapping = {'ANADIR' : _IHEP_ANADIR}))
        raise NotImplementedError(
            '''
            Implementation here needs to take into account new desing for FitSummary
            ''')

    return l_df
# --------------------------------
def main():
    '''
    Entry point
    '''
    cfg     = _get_conf()
    l_df_ss = _get_ss_df(cfg = cfg)

    if cfg.input.q2bin.is_rare:
        l_df_os = _get_os_df(cfg = cfg, df_ss = l_df_ss[0])
    else:
        l_df_os = []

    df = pnd.concat(l_df_ss + l_df_os, ignore_index=True)
    _plot(df = df, cfg_val = cfg)
# --------------------------------
if __name__ == '__main__':
    main()
