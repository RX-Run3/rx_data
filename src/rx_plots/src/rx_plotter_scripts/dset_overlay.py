'''
Script intended to overlay variables from different datasets
e.g. different friend tree versions
'''
import argparse
import os
import mplhep
import matplotlib.pyplot as plt

from pathlib      import Path
from typing       import Final
from contextlib   import ExitStack
from ROOT         import RDF, EnableImplicitMT
from omegaconf    import DictConfig, OmegaConf
from pydantic     import model_validator
from rx_data      import RDFGetter
from rx_common    import Component, Cuts, Trigger, Qsq
from rx_selection import selection        as sel 
from dmu.generic  import utilities        as gut
from dmu.plotting import DsetOverlayConf, Dataset, Plotter1D
from dmu          import LogStore

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])

log = LogStore.add_logger('rx_plots:dset_overlay')
plt.style.use(mplhep.style.LHCb2)
# ----------------------
class Config(DsetOverlayConf):
    selection: dict[Cuts,str]
    sample   : Component
    trigger  : Trigger
    qsq      : Qsq
    # ----------------------
    @model_validator(mode = 'before')
    @classmethod
    def _validate(cls, data):
        plt_dir = data['saving' ]['plt_dir']
        trigger = data['trigger']
        sample  = data['sample' ]
        qsq     = data['qsq'    ]

        trg_nic = Trigger(trigger).value

        data['saving']['plt_dir'] = f'{_ANADIR}/{plt_dir}/{trg_nic}/{sample}/{qsq}'

        return data
    # ----------------------
    @property
    def dict_config(self) -> DictConfig:
        '''
        Omegaconf version of this object
        '''
        data = self.model_dump()

        return OmegaConf.create(data)
# ----------------------
def _parse_args() -> Config:
    '''
    Parses arguments passed by user

    Returns
    --------------
    Instance of configuration data class, built from arguments
    '''
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('-c', '--config' , type=str      , help='Name of config file, e.g. photon_veto', required = True)
    parser.add_argument('-t', '--trigger', type=Trigger  , help='Hlt2 trigger nickname, e.g. rk_ee_os' , required = True)
    parser.add_argument('-s', '--sample' , type=Component, help='Sample, e.g. data_24'                 , required = True)
    parser.add_argument('-q', '--qsq'    , type=Qsq      , help='q2 bin, e.g. central'                 , required = True)
    parser.add_argument('-n', '--ncores' , type=int      , help='Number of cores'                      , default  =    1)
    args = parser.parse_args()

    if args.ncores > 1:
        log.info(f'Using {args.ncores} cores')
        EnableImplicitMT(args.ncores)

    data            = gut.load_data(package = 'rx_plotter_data', fpath = f'dset_overlay/{args.config}.yaml')
    data['trigger'] = args.trigger
    data['sample' ] = args.sample
    data['qsq'    ] = args.qsq

    cfg  = Config(**data)

    return cfg
# ----------------------
def _get_rdf(
    trigger: Trigger,
    sample : Component,
    dset   : Dataset) -> RDF.RNode:
    '''
    Parameters
    ---------------
    trigger: Hlt2 trigger
    sample : MC or data, e.g. data_24
    dset   : Configuration needed to build dataframe

    Returns
    ---------------
    ROOT dataframe
    '''
    ctx_1 = RDFGetter.custom_friends(versions = dset.friends)
    with ExitStack() as stack:
        stack.enter_context(ctx_1)

        gtr = RDFGetter(trigger = trigger, sample = sample)
        rdf = gtr.get_rdf(per_file = False)

    return rdf
# ----------------------
def _get_dataframes(cfg : Config) -> dict[str,RDF.RNode]:
    '''
    Parameters
    -------------
    cfg: Config object

    Returns
    -------------
    Dictionary mapping label of dataset with corresponding dataframe
    '''
    dataframes : dict[str,RDF.RNode] = {}
    for label, dset in cfg.datasets.items():
        rdf         = _get_rdf(
            dset    = dset, 
            sample  = cfg.sample,
            trigger = cfg.trigger)

        rdf = _apply_selection(rdf = rdf, cfg = cfg)

        dataframes[label] = rdf

    return dataframes
# ----------------------
def _apply_selection(rdf : RDF.RNode, cfg : Config) -> RDF.RNode:
    '''
    Parameters
    ----------------
    rdf: ROOT dataframe before any selection
    cfg: Object storing configuration

    Returns
    ----------------
    Dataframe after full selection + custom overriding selection from config
    '''
    with sel.custom_selection(d_sel = cfg.selection):
        rdf         = sel.apply_full_selection(
            rdf     = rdf,
            out_path= cfg.saving.plt_dir,
            q2bin   = cfg.qsq,
            process = cfg.sample,
            trigger = cfg.trigger)

    return rdf
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg   = _parse_args()
    d_rdf = _get_dataframes(cfg = cfg)

    log.info('---------------')
    log.info('Found datasets:')
    log.info('---------------')
    for label in d_rdf:
        log.info(label)

    ptr=Plotter1D(d_rdf=d_rdf, cfg=cfg.dict_config)
    ptr.run()
# ----------------------
if __name__ == '__main__':
    main()
