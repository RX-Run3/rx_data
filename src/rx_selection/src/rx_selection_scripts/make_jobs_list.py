'''
Script that will create a text file with list
of commands to run to apply selection
'''
import os
import glob
import argparse

from functools   import cache
from dataclasses import dataclass

import tqdm
from ROOT                    import RDataFrame
from dmu.logging.log_store   import LogStore

log = LogStore.add_logger('rx_selection:make_jobs_list')
# ----------------------------
@dataclass
class Data:
    '''
    Class used to hold shared attributes
    '''
    data_dir = os.environ['DATADIR']
    version  : str

    l_skip_sample = [
            'Bs_phieta_eplemng_eq_Dalitz_DPC',
            'Bs_phipi0_eplemng_eq_Dalitz_DPC',
            'Bu_KplKplKmn_eq_sqDalitz_DPC',
            'Bu_KplpiplKmn_eq_sqDalitz_DPC',
            'Bu_Lambdacbarppi_Lambdabarmunu_eq_HELAMP_TC',
            'Bu_piplpimnKpl_eq_sqDalitz_DPC',
            'Bu_Kstgamma_Kst_eq_KSpi_DPC_SS',
            'Bd_K1gamma_Kpipi0_eq_mK1270_HighPtGamma_DPC',
            'Bd_Kstpi0_eq_TC_Kst982width100_HighPtPi0',
            'Bd_Dmnpipl_eq_DPC',
            'Bs_Phipi0_gg_eq_DPC_SS',
            'Bs_PhiEta_gg_eq_DPC_SS']

    l_good_trigger = [
            'Hlt2RD_BuToKpMuMu_MVA',
            'Hlt2RD_BuToKpEE_MVA',
            'SpruceRD_BuToHpMuMu',
            'SpruceRD_BuToHpEE',
            'SpruceRD_BuToKpMuMu',
            'SpruceRD_BuToKpEE']
# ----------------------------
@cache
def _sample_and_trigger_from_path(path : str) -> tuple[str,str]:
    l_part = path.split('/')

    sample = l_part[-2]
    trigger= l_part[-1]

    return sample, trigger
# ----------------------------
def _is_good_sample(path : str) -> bool:
    sample, trigger = _sample_and_trigger_from_path(path)

    good_sample = sample not in Data.l_skip_sample
    good_trigger= trigger    in Data.l_good_trigger

    return good_sample and good_trigger
# ----------------------------
def _njobs_from_nentries(nentries : int) -> int:
    if     0   < nentries <=     1000:
        return 0

    if 1_000   < nentries <=   10_000:
        return 1

    if 10_000  < nentries <=   50_000:
        return 5

    if 50_000  < nentries <=  200_000:
        return 10

    if 200_000 < nentries <= 1000_000:
        return 20

    return 40
# ----------------------------
def _njobs_from_path(path : str) -> int:
    rdf = RDataFrame('DecayTree', f'{path}/*.root')
    nentries = rdf.Count().GetValue()
    njob     = _njobs_from_nentries(nentries)

    return njob
# ----------------------------
def _get_sample_info(path : str) -> tuple[str,str,int]:
    njob            = _njobs_from_path(path)
    sample, trigger = _sample_and_trigger_from_path(path)

    return sample, trigger, njob
# ----------------------------
def _get_all_info() -> list[tuple[str,str,int]]:
    sam_wc = f'{Data.data_dir}/RX_run3/{Data.version}/post_ap/*/*'
    log.info(f'Looking for samples in: {sam_wc}')

    l_path = glob.glob(sam_wc)
    nsample= len(l_path)
    if nsample == 0:
        raise FileNotFoundError(f'Found zero samples in: {sam_wc}')

    log.info(f'Found {nsample} samples')

    l_path = [path for path in l_path if _is_good_sample(path)]
    l_info = [ _get_sample_info(path) for path in tqdm.tqdm(l_path, ascii=' -')]

    return l_info
# ----------------------------
def _parse_args() -> None:
    parser = argparse.ArgumentParser(description='Script used to make list of commands to send selection jobs')
    parser.add_argument('-v', '--version' , help='Version of post_ap ntuples, e.g. v1', required=True)
    args = parser.parse_args()

    Data.version = args.version
# ----------------------------
def main():
    '''
    Script starts here
    '''
    _parse_args()

    l_info = _get_all_info()
    text   = ''
    for sample, trigger, njob in l_info:
        if njob == 0:
            log.warning(f'Skipping: {sample}/{trigger}')
            continue

        text += f'job_sel_ihep -d {Data.data_dir}/RX_run3/{Data.version}/post_ap -s {sample} -q central -t {trigger} -p RK -n {njob} -r q2-bdt\n'

    with open('job_list.txt', 'w', encoding='utf-8') as ofile:
        ofile.write(text)
# ----------------------------
if __name__ == '__main__':
    main()
