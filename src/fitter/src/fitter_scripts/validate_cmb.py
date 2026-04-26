'''
Script used to validate PDFs needed to fit combinatorial
'''
import os
import argparse
import pandas   as pnd

from functools    import cache
from ROOT         import RDF # type: ignore
from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import Model, ZFitPlotterConf
from dmu.generic  import utilities as gut
from dmu.plotting import BandPlotter, BandPlotterConf
from rx_selection import selection as sel
from rx_common    import Mass, Qsq, Component, Trigger
from rx_data      import RDFGetter
from fitter       import CmbValidationConfig
from fitter       import CmbValidatorConf
from fitter       import CmbInputConfig
from fitter       import CmbValidator
from fitter       import CmbOutputConfig

log=LogStore.add_logger('rx_fitter:validate_cmb')
# ----------------------
def _get_conf() -> CmbValidatorConf:
    parser = argparse.ArgumentParser(description='Used to perform fits to validate choice of PDF for combinatorial')
    parser.add_argument('-c', '--cutflow', type=       str, help='Cutflow name')
    parser.add_argument('-q', '--q2bin'  , type=       Qsq, help='Q2bin'          , choices =     Qsq)
    parser.add_argument('-M', '--mass'   , type=      Mass, help='Mass to fit'    , choices =    Mass)
    parser.add_argument('-m', '--model'  , type=     Model, help='Fitting model'  , choices =   Model)
    parser.add_argument('-t', '--trigger', type=   Trigger, help='Name of trigger', choices = Trigger)
    parser.add_argument('-s', '--sample' , type= Component, help='Name of sample' , default = Component.data_24)
    args = parser.parse_args()

    data = {
        'q2bin'  : args.q2bin,
        'mass'   : args.mass,
        'model'  : args.model,
        'trigger': args.trigger,
        'sample' : args.sample,
        'cutflow': args.cutflow,
    }

    ana_dir    = Path(os.environ['ANADIR'])

    input      = CmbInputConfig(**data)
    validation = CmbValidationConfig.from_file(fname = 'combinatorial/config.yaml') 

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
    log.info('Parameters not found from cache')

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

    rdf = _get_rdf(cfg = cfg)
    rdf = rdf.Filter(cut)

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
    data= gut.load_data(package = 'fitter_data', fpath = 'combinatorial/plots.yaml')
    data['out_dir'] = str(cfg_val.out_dir)

    cfg = BandPlotterConf(**data) 
    ptr = BandPlotter(cfg = cfg, df = df)
    ptr.plot()
# --------------------------------
def main():
    '''
    Entry point
    '''
    cfg = _get_conf()

    categories : dict[str,str] = {
        '+++' : 'TMath::Abs(total_charge) == 3',
        '+--' : 'TMath::Abs(total_charge) == 1',
        'Both': '(1)',
    }

    l_df : list[pnd.DataFrame] = []
    for label, cut in categories.items():
        df  = _get_pars(
            label = label,
            cut   = cut,
            cfg   = cfg)

        df['Category'] = label
        l_df.append(df)

    df = pnd.concat(l_df)
    _plot(df = df, cfg_val = cfg)
# --------------------------------
if __name__ == '__main__':
    main()
