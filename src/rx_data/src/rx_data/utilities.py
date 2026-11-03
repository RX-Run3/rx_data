'''
Module with utility functions
'''

import re
from dataclasses  import dataclass
from pathlib      import Path

import ap_utilities.decays.utilities as aput
import pandas                        as pnd

from ROOT                   import RDF
from dmu                    import LogStore
from rx_common              import Trigger

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
# ------------------------------------------
def rdf_is_mc(rdf : RDF.RNode) -> bool:
    l_col = [ name.c_str() for name in rdf.GetColumnNames() ]
    for col in l_col:
        if col.endswith('_TRUEID'):
            return True

    return False
# ---------------------------------
def info_from_path(
    path             : str|Path,
    sample_lowercase : bool = True) -> tuple[str,Trigger]:
    '''
    Parameter
    -------------------
    path: Path to a ROOT file
    sample_lowercase: If True (default), it will provide all lowecase sample names

    Returns
    -------------------
    Tuple with sample and HLT2 trigger
    '''
    if isinstance(path, str):
        path = Path(path)

    if   path.name.startswith('dt_') or path.name.startswith('data_'):
        info = _info_from_data_path(path=path)
    elif path.name.startswith('mc_'):
        info = _info_from_mc_path(path=path)
    else:
        raise ValueError(f'File name is not for data or MC: {path.name}')

    sample, trigger_str = info
    trigger = Trigger.from_name(name = trigger_str)
    if sample_lowercase:
        return sample, trigger

    sample = aput.name_from_lower_case(sample)

    return sample, trigger
# ---------------------------------
def _info_from_mc_path(path : Path) -> tuple[str,str]:
    '''
    Will return information from path to file
    '''
    mtch = re.match(Data.mc_rgx, path.name)
    if not mtch:
        raise ValueError(f'Cannot extract information from MC file:\n\n{path.name}\n\nUsing {Data.mc_rgx}')

    try:
        [sample, line, _] = mtch.groups()
    except ValueError as exc:
        raise ValueError(f'Expected three elements in: {mtch.groups()}') from exc

    return sample, line
# ---------------------------------
def _info_from_data_path(path : Path) -> tuple[str,str]:
    '''
    Parameters
    -----------------
    path: Path to ROOT file

    Returns
    -----------------
    Tuple with sample name and trigger name
    '''
    mtch = re.match(Data.dt_rgx, path.name)
    if not mtch:
        raise ValueError(f'Cannot find kind in:\n\n{path.name}\n\nusing\n\n{Data.dt_rgx}')

    try:
        [sample, line, _] = mtch.groups()
    except ValueError as exc:
        raise ValueError(f'Expected three elements in: {mtch.groups()}') from exc

    sample = sample.replace('_turbo_rd_', '_')
    sample = sample.replace('_turbo_'   , '_')
    sample = sample.replace('_full_'    , '_')

    return sample, line
# ---------------------------------
def df_from_rdf(
    rdf       : RDF.RNode,
    drop_nans : bool) -> pnd.DataFrame:
    '''
    Parameters
    ------------------
    rdf      : ROOT dataframe
    drop_nans: If true it will remove events (rows) with NaNs

    Returns
    ------------------
    Pandas dataframe with contents of ROOT dataframe
    '''
    rdf    = _preprocess_rdf(rdf)
    l_col  = [ name.c_str() for name in rdf.GetColumnNames() if _pick_column(name=name.c_str()) ]
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

    if has_nans and drop_nans:
        df   = df.dropna()
        ndrp = len(df)
        log.warning(f'Dropping columns with NaNs {ntot} -> {ndrp}')

    columns = df.select_dtypes(include=['object']).columns.tolist()
    if not columns:
        return df

    for column in columns:
        log.info(column)

    raise ValueError('Columns with object type')
# ------------------------------------------
def _preprocess_rdf(rdf: RDF.RNode) -> RDF.RNode:
    rdf = _preprocess_lepton(rdf, 'L1')
    rdf = _preprocess_lepton(rdf, 'L2')

    return rdf
# ------------------------------------------
def _preprocess_lepton(rdf : RDF.RNode, lep : str) -> RDF.RNode:
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
    to_keep  = ['EVENTNUMBER', 'RUNNUMBER', 'nPVs']

    # Needed to identify electrons, muons do not need brem correction
    to_keep += ['L1_ID'      , 'L2_ID']

    # For q2 smearing
    to_keep += ['nbrem'      , 'block', 'Jpsi_TRUEM', 'B_TRUEM']

    # To re-use old DIRA in case new DIRA cannot be calculated
    to_keep += ['Jpsi_DIRA_OWNPV']

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
