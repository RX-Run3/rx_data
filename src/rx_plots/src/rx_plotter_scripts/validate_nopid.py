'''
Script used to plot PID distributions from:

    - Samples with PID removed and original ones
    - Check that the distributions agree when the former ones have had the PID added
'''

import os
import re
import copy
import glob
import argparse

import mplhep
import matplotlib.pyplot as plt

from ROOT                    import RDF
from dmu                     import LogStore
from ap_utilities.decays     import utilities          as aput
from dmu.plotting            import Plotter1D          as Plotter
from dmu.generic             import utilities          as gut
from dmu.generic             import version_management as vmn
from omegaconf               import DictConfig, OmegaConf
from rx_common               import Component, Project
from rx_common               import Trigger
from rx_data                 import RDFGetter

log = LogStore.add_logger('rx_plots:validate_nopid')

_ANADIR = os.environ['ANADIR']
# ----------------------------
class Data:
    '''
    Data class
    '''
    cfg     : dict
    weight  : str
    samples : dict[Component,Trigger] # Dictionary with sample -> trigger name
    regex   = r'mc_\w+_\d{8}_(.*)_(Hlt2.*MVA)_\w+\.root' # Needed to extract sample and trigger name

    plt.style.use(mplhep.style.LHCb2)
# ----------------------------
def _parse_args() -> argparse.Namespace:
    '''
    Parses arguments passed by user

    Returns
    --------------
    Instance of configuration data class, built from arguments
    '''

    parser = argparse.ArgumentParser(description='Runs validation of simulation without PID')
    args = parser.parse_args()

    return args
# ----------------------------
def _get_rdf(component : Component, trigger : Trigger, has_pid : bool) -> RDF.RNode:
    if not has_pid:
        trigger = Trigger.from_name(f'{trigger}_noPID')

    weight = '1.0' if has_pid else Data.weight

    with RDFGetter.exclude_friends(names=[
        'brem_track_2',
        'hop',
        'mva',
        'swp_cascade',
        'swp_jpsi_misid']):
        gtr = RDFGetter(sample=component, trigger=trigger)
        rdf = gtr.get_rdf(per_file=False)
        rdf = rdf.Define('weights', weight)

    return rdf
# ----------------------------
def _compare(
        sample    : str,
        rdf_nopid : RDF.RNode,
        rdf_yspid : RDF.RNode,
        rdf_xcpid : RDF.RNode) -> None:

    d_rdf={'Original'             : rdf_yspid,
           'New with PID'         : rdf_xcpid,
           f'{Data.weight} x New' : rdf_nopid}

    cfg   = _get_config_with_title(sample=sample)
    ptr   = Plotter(d_rdf=d_rdf, cfg=cfg)
    ptr.run()
# ----------------------------
def _get_config_with_title(sample : str) -> DictConfig:
    cfg  = copy.deepcopy(Data.cfg)

    for _, settings in cfg['plots'].items():
        settings['title'] = sample
        name = settings['name']
        settings['name'] = f'{name}_{sample}'

    return OmegaConf.create(cfg)
# ----------------------------
def _load_config(channel : str) -> None:
    cfg = gut.load_data(
        package='rx_plotter_data',
        fpath  =f'no_pid/{channel}.yaml')

    plt_dir = f'{_ANADIR}/plots/checks/validate_nopid/{channel}'
    cfg['saving'] = {'plt_dir' : plt_dir}

    Data.cfg = cfg
# ----------------------------
def _apply_pid(rdf : RDF.RNode) -> RDF.RNode:
    d_cut = Data.cfg['selection']['cuts']

    for name, expr in d_cut.items():
        rdf = rdf.Filter(expr, name)

    rdf = rdf.Redefine('weights', '1.0')

    del Data.cfg['selection']['cuts']

    return rdf
# ----------------------------
def _get_component_trigger(fpath : str) -> tuple[Component,Trigger]:
    '''
    Parameters
    ---------------
    fpath : path to ROOT file

    Returns
    ---------------
    tuple with sample and HLT trigger name
    '''
    fname = os.path.basename(fpath)
    mtch  = re.match(Data.regex, fname)
    if mtch is None:
        raise ValueError(f'Cannot match with {Data.regex} in {fname}')

    sample, trigger = mtch.groups()
    sample = aput.name_from_lower_case(sample)
    log.debug(f'Found: {sample}/{trigger}')

    return Component.from_sample(sample), Trigger.from_name(trigger)
# ----------------------------
def _load_samples() -> None:
    '''
    This is meant to fill Data.samples
    '''
    fdir    = f'{_ANADIR}/Data/{Project.rk_no_pid}/main'
    dpath   = vmn.get_last_version(dir_path=fdir, version_only=False)
    file_wc = f'{dpath}/*.root'
    l_fpath = glob.glob(file_wc)
    if len(l_fpath) == 0:
        raise FileNotFoundError(f'No files found in: {file_wc}')

    l_component_trigger = [ _get_component_trigger(fpath=fpath) for fpath in l_fpath ]
    Data.samples        = dict(l_component_trigger)
# ----------------------------
def main(args : DictConfig | None = None):
    '''
    Start here
    '''
    if args is None:
        _parse_args()

    _load_samples()

    for component, trigger in Data.samples.items():
        if component == Component.bpkpjpsiee:
            continue

        if 'btosllball' in component.sample:
            Data.weight  = '0.5' if trigger.is_muon else '0.1'
        elif component == Component.bppijpsiee:
            Data.weight  = '0.5' if trigger.is_muon else '2e-2'
        else:
            Data.weight  = '0.5' if trigger.is_muon else '1e-4'

        _load_config(channel=trigger.channel)

        rdf_nopid = _get_rdf(component = component, trigger=trigger, has_pid=False)
        rdf_yspid = _get_rdf(component = component, trigger=trigger, has_pid=True )
        rdf_xcpid = _apply_pid(rdf_nopid)

        _compare(
            sample    = component,
            rdf_nopid = rdf_nopid,
            rdf_yspid = rdf_yspid,
            rdf_xcpid = rdf_xcpid)
# ----------------------------
if __name__ == '__main__':
    main()
