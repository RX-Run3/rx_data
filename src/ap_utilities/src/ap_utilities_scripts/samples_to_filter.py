'''
This script will create a YAML file needed to build
the YAML file needed to submit filtering jobs to the grid
'''

import re
import argparse

import apd
from typing                 import Any, Final
from apd                    import SampleCollection
from dataclasses            import dataclass
from dmu.logging.log_store  import LogStore
from dmu.generic            import utilities as gut
from rx_data.filtered_stats import FilteredStats

log = LogStore.add_logger('ap_utilities:samples_to_filter')
fst = FilteredStats(analysis='rx', versions=[7, 10])
# ----------------------
@dataclass
class Sample:
    '''
    Class meant to represent an MC sample
    '''
    event_type : str
    name       : str
    version    : str
    block      : str
    polarity   : str
# ----------------------
@dataclass
class Config:
    '''
    Class used to store configuration
    '''
    versions : Final[list[str]]
    analysis : Final[str]
# ----------------------
def _parse_args() -> Config:
    parser = argparse.ArgumentParser(description='Script needed to parse samples from AP productions')
    parser.add_argument('-v', '--versions', nargs='+', type=str, help='Versions of AP ntuples, e.g. v1r3788', required=True)
    parser.add_argument('-a', '--analysis',            type=str, help='Analysis, needed to pick up event types', required=True, choices=['rk', 'rkst'])
    parser.add_argument('-l', '--log_lvl' ,            type=int, help='Logging level', default=20, choices=[5, 10, 20, 30, 40, 50])
    args = parser.parse_args()

    LogStore.set_level('ap_utilities:samples_to_filter', args.log_lvl)
    cfg  = Config(versions=args.versions, analysis=args.analysis)

    return cfg
# ----------------------
def _get_samples(cfg : Config) -> list[Sample]:
    '''
    Parameters
    -------------
    cfg: Config object

    Returns
    -------------
    List of instances of Sample, storing needed information on samples
    '''
    log.info('Retrieving samples')

    dset = apd.get_analysis_data(working_group='RD', analysis='rx_2024')
    scol = dset.all_samples()
    if not isinstance(scol, SampleCollection):
        raise RuntimeError('Cannot extract SampleCollection instance')

    l_sample = []
    for version in cfg.versions:
        log.info(version)
        l_sample+= _samples_from_collection(scol=scol, analysis=cfg.analysis, version=version)

    return l_sample
# ----------------------
def _samples_from_collection(scol : SampleCollection, analysis : str, version : str) -> list[Sample]:
    '''
    Parameters
    -------------
    scol: Object storing sample information, from APD
    analysis: Either rk or rkst
    version : Version of aprod

    Returns
    -------------
    List of Sample instances with information on ntupled sample
    '''
    l_evt_type = _types_from_analysis(analysis=analysis)

    l_sample = []
    for evt_type in l_evt_type:
        log.debug(evt_type)
        scol_flt = scol.filter(eventtype=evt_type, version=version)
        if len(scol_flt) == 0:
            continue

        l_sample += [ _build_sample(version=version, event_type=evt_type, scol=entry) for entry in scol_flt if entry is not None ]

    log.info(f'Found {len(l_sample)} samples')
    log.info('')

    return l_sample
# ----------------------
def _build_sample(version : str, event_type : str, scol : dict[str,Any]) -> Sample|None:
    '''
    Parameters
    -------------
    version   : AP version
    event_type: Event type
    scol      : Object from APD holding information on sample

    Returns
    -------------
    Sample instance with information on sample
    '''
    if _skip_sample(scol=scol):
        return

    name      = scol['name']
    block_rgx = r'_(w\d{2}_\d{2})_'

    log.debug(name)

    val = re.search(block_rgx, name)
    if val is None:
        raise ValueError(f'Cannot extract block information from: {name}')

    block = val.group(1)

    if   '_magup_'   in name:
        polarity = 'magup'
    elif '_magdown_' in name:
        polarity = 'magdown'
    else:
        raise ValueError(f'Cannot find polarity in: {name}')

    return Sample(
        name      = name,
        event_type= event_type,
        polarity  = polarity,
        block     = block,
        version   = version)
# ----------------------
def _skip_sample(scol : dict[str,Any]) -> bool:
    '''
    Parameters
    -------------
    scol: Dictionary with sample information from APD

    Returns
    -------------
    True if this is meant to be skipped
    '''
    name = scol['name']
    l_bad_substr = ['sprucing', 'spr,', 'hlt1bug', '_mcdt']
    for bad_substr in l_bad_substr:
        if bad_substr in name:
            log.verbose(f'Skipping: {name}')
            return True

    return False
# ----------------------
def _types_from_analysis(analysis : str) -> list[str]:
    '''
    Parameters
    -------------
    analysis: Either rk or rkst

    Returns
    -------------
    List of event types
    '''
    cfg = gut.load_conf(package='ap_utilities_data', fpath='analyses/analyses.yaml')
    if analysis == 'rk':
        l_et = cfg.rk[0]
        l_et = list(map(str, l_et ))
        return sorted(l_et)

    if analysis == 'rkst':
        rk = cfg.rk[0]
        rx = cfg.rx[0] + cfg.rx[1]
        l_et = [ etype for etype in rx if etype not in rk ]
        l_et = list(map(str, l_et ))
        return sorted(l_et)

    raise ValueError(f'Invalid analysis: {analysis}')
# ----------------------
def _remove_already_filtered(l_sample : list[Sample]) -> list[Sample]:
    '''
    Parameters
    -------------
    l_sample: List of instances of Sample

    Returns
    -------------
    Same list, but with the samples already filtered, removed
    '''
    l_sample_flt = []
    log.info('Picking unfiltered samples')
    for sample in l_sample:
        etp = sample.event_type
        blk = sample.block
        mag = sample.polarity

        if fst.exists(event_type=etp, block=blk, polarity=mag):
            continue

        log.info(f'{sample.version:<15}{sample.name}')

        l_sample_flt.append(sample)

    log.info(f'Found {len(l_sample_flt)} samples')

    return l_sample_flt
# ----------------------
def main():
    '''
    Entry point
    '''
    cfg      = _parse_args()
    l_sample = _get_samples(cfg=cfg)
    l_sample = _remove_already_filtered(l_sample=l_sample)
# ----------------------
if __name__ == '__main__':
    main()
