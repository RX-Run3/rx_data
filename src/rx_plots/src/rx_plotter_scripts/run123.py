'''
Script meant to do comparisons of variables between Run1,2 and 3
'''
import os
import argparse

import mplhep
from ROOT                    import RDF
from omegaconf               import DictConfig
from dmu.generic             import utilities as gut
from dmu.logging.log_store   import LogStore
from dmu.plotting.plotter_1d import Plotter1D
from rx_selection            import selection as sel
from rx_data.rdf_getter      import RDFGetter
from rx_data.rdf_getter12    import RDFGetter12

log=LogStore.add_logger('rx_plotter:run123')
# ----------------------
class Data:
    '''
    Class meant to be used to share attributes
    '''
    cfg     : DictConfig
    ana_dir = os.environ['ANADIR']
# ----------------------
def _initialize() -> None:
    '''
    Nothing, this function initializes the state of the Data class
    '''
    args = _parse_args()
    _set_logs(level=args.logl)
    cfg  = gut.load_conf(package='rx_plotter_data', fpath=f'run123/{args.conf}.yaml')

    plt_dir  = cfg.saving.plt_dir
    cfg.saving.plt_dir = f'{Data.ana_dir}/{plt_dir}'

    mplhep.style.use('LHCb2')

    Data.cfg = cfg
# ----------------------
def _set_logs(level : int) -> None:
    '''
    Parameters
    -------------
    level: Logging level

    Returns
    -------------
    Nothing
    '''
    LogStore.set_level(name='dmu:plotting:Plotter', value=level)
# ----------------------
def _get_rdf(dset : str) -> RDF.RNode:
    '''
    Parameters
    -------------
    dset: Label for dataset, e.g. 2024, run12

    Returns
    -------------
    ROOT dataframe with corresponding data
    '''
    sample = Data.cfg.input.sample
    trigger= Data.cfg.input.trigger

    if   dset == '2024':
        gtr = RDFGetter(sample=sample, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)
        rdf = sel.apply_full_selection(rdf=rdf, q2bin='jpsi', process=sample, trigger=trigger)
    elif dset == 'run12':
        gtr = RDFGetter12(
            sample =sample,
            trigger=trigger,
            dset   ='all')
        rdf = gtr.get_rdf()
    else:
        raise NotImplementedError(f'Invalid dataset {dset}')

    rdf = _apply_definitions(rdf=rdf, dset=dset)

    return rdf
# ----------------------
def _apply_definitions(rdf : RDF.RNode, dset : str) -> RDF.RNode:
    '''
    Parameters
    -------------
    rdf: ROOT dataframe
    dset: Dataset identifying definitions, i.e. run12

    Returns
    -------------
    Dataframe with definitions applied
    '''
    log.info(f'Applying definitions for: {dset}')

    d_def = Data.cfg.branches[dset]
    for name, expr in d_def.items():
        log.debug(f'{name:<30}{expr}')
        rdf = rdf.Define(name, expr)

    return rdf
# ----------------------
def _get_dataframes() -> dict[str,RDF.RNode]:
    '''
    Returns
    -------------
    Dictionary with:
    Key  : Label for dataset, e.g. run12, 2014
    Value: Dataframe with that data corresponding to sample and trigger from config
    '''
    d_rdf = {}
    for dataset in Data.cfg.comparison:
        d_rdf[dataset] = _get_rdf(dset=dataset)

    return d_rdf
# ----------------------
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Script used to make comparisons of variables between Run1,2 and 3')
    parser.add_argument('-c', '--conf' , type=str, help='Name of config file, e.g. mass', required=True)
    parser.add_argument('-l', '--logl' , type=int, help='Logging level', default=20)
    args = parser.parse_args()

    return args
# ----------------------
def main():
    '''
    Entry point
    '''
    _initialize()
    d_sel = Data.cfg.cuts

    with sel.custom_selection(d_sel=d_sel),\
        RDFGetter12.add_selection(d_sel=d_sel):
        d_rdf = _get_dataframes()

    ptr   = Plotter1D(d_rdf=d_rdf, cfg=Data.cfg)
    ptr.run()
# ----------------------
if __name__ == '__main__':
    main()
