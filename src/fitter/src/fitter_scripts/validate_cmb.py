'''
Script used to validate PDFs needed to fit combinatorial
'''
import argparse

from dmu       import LogStore
from dmu.stats import Model
from rx_common import Mass, Qsq, Component, Trigger
from rx_data   import RDFGetter
from fitter    import CmbValidationConfig
from fitter    import CmbValidatorConf
from fitter    import CmbInputConfig
from fitter    import CmbValidator

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

    input      = CmbInputConfig(**data)
    validation = CmbValidationConfig.from_file(fname = 'combinatorial/config.yaml') 

    return CmbValidatorConf(
        input      = input,
        validation = validation)
# --------------------------------
def main():
    '''
    Entry point
    '''
    cfg = _get_conf()
    gtr = RDFGetter(
        trigger= cfg.input.trigger,
        sample = cfg.input.sample)
    rdf = gtr.get_rdf(per_file = False)

    obj = CmbValidator(
        rdf = rdf,
        cfg = cfg)
    res = obj.run()
# --------------------------------
if __name__ == '__main__':
    main()
