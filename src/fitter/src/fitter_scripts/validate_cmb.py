'''
Script used to validate PDFs needed to fit combinatorial
'''
import os
import argparse
import pandas   as pnd

from pathlib      import Path
from dmu          import LogStore
from dmu.stats    import Model, ZFitPlotterConf
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

    output     = CmbOutputConfig(
        plots    = ZFitPlotterConf.default(),
        dir_path = ana_dir / 'combinatorial/validation'
    )

    return CmbValidatorConf(
        input      = input,
        output     = output,
        validation = validation)
# ----------------------
def _get_pars(cfg : CmbValidatorConf) -> pnd.DataFrame:
    out_path = cfg.output.dir_path / 'parameters.parquet'
    if out_path.exists():
        log.info(f'Parameters found from cache, loading: {out_path}')
        return pnd.read_parquet(path = out_path)

    log.info('Parameters not found from cache')

    gtr = RDFGetter(
        trigger= cfg.input.trigger,
        sample = cfg.input.sample)
    rdf = gtr.get_rdf(per_file = False)

    with sel.custom_selection(d_sel = cfg.validation.selection):
        rdf = sel.apply_full_selection(
            rdf     = rdf,
            out_path= cfg.output.out_dir(),
            q2bin   = cfg.input.q2bin,
            process = cfg.input.sample,
            trigger = cfg.input.trigger)

    obj = CmbValidator(
        rdf = rdf,
        cfg = cfg)
    res = obj.run()

    log.info(f'Caching to: {out_path}')
    res.df.to_parquet(path = out_path)

    return res.df
# --------------------------------
def main():
    '''
    Entry point
    '''
    cfg = _get_conf()
    df  = _get_pars(cfg = cfg)

    print(df)
# --------------------------------
if __name__ == '__main__':
    main()
