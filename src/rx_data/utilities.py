'''
Module with utility functions
'''
# pylint: disable=too-many-return-statements

import os
import re
from dataclasses            import dataclass

import pandas as pnd
from ROOT                   import RDataFrame
from dmu.logging.log_store  import LogStore

log   = LogStore.add_logger('rx_data:utilities')
# ---------------------------------
@dataclass
class Data:
    '''
    Class used to hold shared data
    '''
    # pylint: disable = invalid-name
    # Need to call var Max instead of max

    dt_rgx  = r'(data_\d{2}_.*c\d)_(Hlt2RD_.*(?:EE|MuMu|misid|cal|MVA|LL|DD))_?(\d{3}_\d{3}|[a-z0-9]{10})?\.root'
    mc_rgx  = r'mc_.*_\d{8}_(.*)_(\w+RD_.*)_(\d{3}_\d{3}|\w{10}).root'
# ---------------------------------
def is_mc(sample : str) -> bool:
    '''
    Given a sample name, it will check if it is MC or data
    '''

    if sample.startswith('DATA'):
        return False

    return True
# ---------------------------------
def is_ee(trigger : str) -> bool:
    '''
    Given Hlt2 trigger name, it will tell if it belongs to
    muon or electron channel
    '''
    # From https://gitlab.cern.ch/lhcb/Moore/-/blob/master/Hlt/Hlt2Conf/python/Hlt2Conf/lines/rd/b_to_xll_hlt2_mva.py?ref_type=heads

    ee_trig = [
            'Hlt2RD_BuToKpEE_MVA', 
            'Hlt2RD_BuToKpEE_SameSign_MVA',
            'Hlt2RD_BuToKpEE_MVA_misid',
            'Hlt2RD_BuToKpEE_MVA_cal',
            # ----
            'Hlt2RD_B0ToKpPimEE_MVA',
            'Hlt2RD_B0ToKpPimEE_SameSign_MVA',
            'Hlt2RD_B0ToKpPimEE_MVA_misid',
            'Hlt2RD_B0ToKpPimEE_MVA_cal',
            # ----
            'Hlt2RD_LbTopKEE_MVA',
            'Hlt2RD_LbTopKEE_SameSign_MVA',
            'Hlt2RD_LbTopKEE_MVA_misid',
            # ----
            'Hlt2RD_BsToPhiEE_MVA',
            'Hlt2RD_BsToPhiEE_SameSign_MVA',
            'Hlt2RD_BsToPhiEE_MVA_misid']

    mm_trig = [
            'Hlt2RD_BuToKpMuMu_MVA',
            'Hlt2RD_BuToKpMuMu_SameSign_MVA',
            # ----
            'Hlt2RD_B0ToKpPimMuMu_MVA',
            'Hlt2RD_B0ToKpPimMuMu_SameSign_MVA',
            # ----
            'Hlt2RD_LbTopKMuMu_SameSign_MVA',
            'Hlt2RD_LbTopKMuMu_MVA',
            # ----
            'Hlt2RD_BsToPhiMuMu_MVA',
            'Hlt2RD_BsToPhiMuMu_SameSign_MVA']

    em_trig = [
            'Hlt2RD_BuToKpMuE_MVA',
            'Hlt2RD_B0ToKpPimMuE_MVA',
            'Hlt2RD_LbTopKMuE_MVA',
            'Hlt2RD_BsToPhiMuE_MVA']

    non_ee = mm_trig + em_trig

    if trigger in ee_trig:
        return True

    if trigger in non_ee:
        return False

    raise ValueError(f'Trigger {trigger} not found')
# ---------------------------------
def info_from_path(path : str) -> tuple[str,str]:
    '''
    Will pick a path to a ROOT file
    Will return tuple with information associated to file
    This is needed to name output file and directories
    '''

    name = os.path.basename(path)
    if   name.startswith('dt_') or name.startswith('data_'):
        info = _info_from_data_path(path)
    elif name.startswith('mc_'):
        info = _info_from_mc_path(path)
    else:
        log.error(f'File name is not for data or MC: {name}')
        raise ValueError

    return info
# ---------------------------------
def _info_from_mc_path(path : str) -> tuple[str,str]:
    '''
    Will return information from path to file
    '''
    name = os.path.basename(path)
    mtch = re.match(Data.mc_rgx, name)
    if not mtch:
        raise ValueError(f'Cannot extract information from MC file:\n\n{name}\n\nUsing {Data.mc_rgx}')

    try:
        [sample, line, _] = mtch.groups()
    except ValueError as exc:
        raise ValueError(f'Expected three elements in: {mtch.groups()}') from exc

    return sample, line
# ---------------------------------
def _info_from_data_path(path : str) -> tuple[str,str]:
    '''
    Will get info from data path
    '''
    name = os.path.basename(path)
    mtch = re.match(Data.dt_rgx, name)
    if not mtch:
        raise ValueError(f'Cannot find kind in:\n\n{name}\n\nusing\n\n{Data.dt_rgx}')

    try:
        [sample, line, _] = mtch.groups()
    except ValueError as exc:
        raise ValueError(f'Expected three elements in: {mtch.groups()}') from exc

    sample = sample.replace('_turbo_', '_')
    sample = sample.replace('_full_' , '_')

    return sample, line
# ---------------------------------
def df_from_rdf(rdf : RDataFrame) -> pnd.DataFrame:
    '''
    Utility method needed to get pandas dataframe from ROOT dataframe
    '''
    rdf    = _preprocess_rdf(rdf)
    l_col  = [ name.c_str() for name in rdf.GetColumnNames() if _pick_column(name.c_str()) ]
    d_data = rdf.AsNumpy(l_col)
    df     = pnd.DataFrame(d_data)

    ntot     = len(df)
    has_nans = False
    log.debug(60 * '-')
    log.debug(f'{"Variable":<20}{"NaNs":<20}{"%":<20}')
    log.debug(60 * '-')
    for name, sr in df.items():
        nnan = sr.isna().sum()
        perc = 100 * nnan / ntot
        if perc > 0:
            has_nans = True
            log.debug(f'{name:<20}{nnan:<20}{perc:<20.2f}')
    log.debug(60 * '-')

    if has_nans:
        df   = df.dropna()
        ndrp = len(df)
        log.warning(f'Dropping columns with NaNs {ntot} -> {ndrp}')

    return df
# ------------------------------------------
def _preprocess_rdf(rdf: RDataFrame) -> RDataFrame:
    rdf = _preprocess_lepton(rdf, 'L1')
    rdf = _preprocess_lepton(rdf, 'L2')
    rdf = _preprocess_lepton(rdf,  'H')

    return rdf
# ------------------------------------------
def _preprocess_lepton(rdf : RDataFrame, lep : str) -> None:
    # Make brem flag an int (will make things easier later)
    rdf = rdf.Redefine(f'{lep}_HASBREMADDED'        , f'int({lep}_HASBREMADDED)')
    # If there is no brem, make energy zero
    rdf = rdf.Redefine(f'{lep}_BREMHYPOENERGY'      , f'{lep}_HASBREMADDED == 1 ? {lep}_BREMHYPOENERGY : 0')
    # If track based energy is NaN, make it zero
    rdf = rdf.Redefine(f'{lep}_BREMTRACKBASEDENERGY', f'{lep}_BREMTRACKBASEDENERGY == {lep}_BREMTRACKBASEDENERGY ? {lep}_BREMTRACKBASEDENERGY : 0')

    return rdf
# ------------------------------------------
def _pick_column(name : str) -> bool:
    # To make friend trees and align entries
    to_keep  = ['EVENTNUMBER', 'RUNNUMBER']
    # For q2 smearing
    to_keep += ['nbrem'      , 'block', 'Jpsi_TRUEM', 'B_TRUEM']
    # To recalculate DIRA
    to_keep += ['Jpsi_BPVX', 'Jpsi_BPVY', 'Jpsi_BPVZ']
    to_keep += [   'B_BPVX',    'B_BPVY',    'B_BPVZ']
    to_keep += ['Jpsi_END_VX', 'Jpsi_END_VY', 'Jpsi_END_VZ']
    to_keep += [   'B_END_VX',    'B_END_VY',    'B_END_VZ']

    if name in to_keep:
        return True

    if name.endswith('MC_ISPROMPT'):
        return False

    if name.startswith('H_BREM'):
        return False

    if name.startswith('H_TRACK_P'):
        return False

    if '_TRUE' in name:
        return False

    not_l1 = not name.startswith('L1')
    not_l2 = not name.startswith('L2')
    not_kp = not name.startswith('H')

    if not_l1 and not_l2 and not_kp:
        return False

    if 'BREMTRACKBASEDENERGY' in name:
        return True

    if 'HASBREMADDED' in name:
        return True

    if 'NVPHITS' in name:
        return False

    if 'CHI2' in name:
        return False

    if 'HYPOID' in name:
        return False

    if 'HYPODELTA' in name:
        return False

    if 'PT' in name:
        return True

    if 'ETA' in name:
        return True

    if 'PHI' in name:
        return True

    if 'PX' in name:
        return True

    if 'PY' in name:
        return True

    if 'PZ' in name:
        return True

    if 'BREMHYPO' in name:
        return True

    return False
# ------------------------------------------
