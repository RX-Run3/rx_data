'''
Script used to provide blocks of MC samples in a YAML file
Needed to write YAML config for post_ap
'''
import re
import argparse
from functools           import cache
from importlib.resources import files


import yaml
import ap_utilities.decays.utilities as aput

from apd                    import AnalysisData, SampleCollection
from dmu.logging.log_store  import LogStore

log=LogStore.add_logger('dmu:post_ap_scripts:dump_samples')
# ----------------------------------------------
class IndentedDumper(yaml.Dumper):
    '''
    Class needed to create indentation when saving lists as values of dictionaries in YAML files
    '''
    def increase_indent(self, flow=False, indentless=False):
        _ = indentless
        return super().increase_indent(flow, False)
# ----------------------------------------------
class Data:
    '''
    Data class used to store shared data
    '''
    regex = r'mc_\d{2}_(w\d{2}_\d{2})_.*'
    l_vers: list[str]
    group : str
    prod  : str

    l_analysis : list[str]
# ----------------------------------------------
def _block_from_name(name : str) -> str:
    mtch = re.match(Data.regex, name)
    if not mtch:
        raise ValueError(f'Cannot find version in: {name}')

    return mtch.group(1)
# ----------------------------------------------
def _get_samples(samples : SampleCollection) -> dict[str,list[str]]:
    d_data   = {}
    sample : dict[str,str]
    for sample in samples:
        vers = sample['version']
        if vers not in Data.l_vers:
            continue

        name = sample['name']
        if not name.startswith('mc_'):
            continue

        block = _block_from_name(name)
        key = f'{block}_{vers}'
        if key not in d_data:
            d_data[key] = []

        d_data[key].append(name)

    if len(d_data) == 0:
        raise ValueError('No samples found')

    for l_sam in d_data.values():
        l_sam.sort()

    return d_data
# ----------------------------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to create a list of MC samples in YAML, split by sim production for a given (latest) version of the AP.')
    parser.add_argument('-v', '--vers'    , nargs='+', help='Versions of AP, e.g. v1r2266', required=True)
    parser.add_argument('-p', '--prod'    , type =str, help='Production, e.g. rd_ap_2024' , required=True)
    parser.add_argument('-g', '--group'   , type =str, help='Group, e.g. rd'              , required=True)
    parser.add_argument('-l', '--loglvl'  , type =int, help='Log level'                   , choices=[10, 20, 30], default=20)
    parser.add_argument('-a', '--analyses', nargs='+', help='Analyses for which to check if samples are missing, e.g. RK, RKst')
    args = parser.parse_args()

    Data.l_vers     = args.vers
    Data.group      = args.group
    Data.prod       = args.prod
    Data.l_analysis = args.analyses

    LogStore.set_level('dmu:post_ap_scripts:dump_samples', args.loglvl)
# ----------------------------------------------
@cache
def _load_samples() -> dict[str, list[str]]:
    path = files('post_ap_data').joinpath('samples/sample_run3.yaml')
    path = str(path)
    with open(path, encoding='utf-8') as ifile:
        d_analysis = yaml.safe_load(ifile)

    return d_analysis
# ----------------------------------------------
def _is_sample_found(sample_needed :  str, l_sample_found : list[str]) -> bool:
    if sample_needed.startswith('DATA_'):
        return True

    sample_needed = sample_needed.lower()

    log.debug(f'Looking for {sample_needed}')

    for sample_found in l_sample_found:
        if sample_needed in sample_found:
            log.debug(f'{sample_needed:<20}{sample_found}')
            return True

    return False
# ----------------------------------------------
def _get_missing_samples(l_samples_found : list[str], block_period : str) -> dict[str,str]:
    d_sam            = _load_samples()
    l_samples_needed : list[str] = []
    for analysis in Data.l_analysis:
        if analysis not in d_sam:
            log.warning(f'Analysis {analysis} not found, skipping')
            continue

        l_samples_needed += d_sam[analysis]

    d_missing = {
        aput.read_event_type(sample_needed) : sample_needed
        for sample_needed in l_samples_needed
        if not _is_sample_found(sample_needed, l_samples_found) }

    nmiss = len(d_missing)
    if nmiss > 0:
        log.warning(f'Missing {nmiss} samples in {block_period}')
    else:
        log.info(f'No missing samples in {block_period}')

    return d_missing
# ----------------------------------------------
def _save_missing(d_sam : dict[str,list[str]]) -> None:
    if Data.l_analysis is None:
        log.info('No analysis specified, will not check for missing samples')
        return

    d_miss = {}
    for block_period, l_sam in d_sam.items():
        l_missing = _get_missing_samples(l_sam, block_period)
        d_miss[block_period] = l_missing

    with open(f'{Data.group}_{Data.prod}_miss.yaml', 'w', encoding='utf-8') as ofile:
        yaml.dump(d_miss, ofile, Dumper=IndentedDumper)

    l_miss : list[str] = []
    for l_evtid in d_miss.values():
        l_miss += l_evtid

    s_evtid = set(l_miss)
    with open(f'{Data.group}_{Data.prod}_miss.txt', 'w', encoding='utf-8') as ofile:
        text = '\n'.join(s_evtid)
        ofile.write(text)
# ----------------------------------------------
def _merge_versions(d_data : dict[str,list[str]]) -> dict[str,list[str]]:
    d_merged = {}
    for key, l_val in d_data.items():
        l_part  = key.split('_')
        l_part  = l_part[:-1]
        new_key = '_'.join(l_part)

        if new_key not in d_merged:
            d_merged[new_key] = []

        d_merged[new_key] += l_val

    return d_merged
# ----------------------------------------------
def main():
    '''
    Script starts here
    '''
    _parse_args()

    datasets = AnalysisData(Data.group, Data.prod)
    samples  = datasets.all_samples()

    if not isinstance(samples, SampleCollection):
        raise ValueError('Samples object is not a samples collection')

    d_data = _get_samples(samples)
    with open(f'{Data.group}_{Data.prod}.yaml', 'w', encoding='utf-8') as ofile:
        yaml.dump(d_data, ofile, Dumper=IndentedDumper)

    d_data = _merge_versions(d_data)
    _save_missing(d_data)
# ----------------------------------------------
if __name__ == '__main__':
    main()
