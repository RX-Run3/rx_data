'''
Script used to calculate Geometric acceptances through AcceptanceCalculator and save them to JSON
'''

import os
import argparse

import mplhep
import pandas                   as pnd
import matplotlib.pyplot        as plt

from typing         import Final
from pathlib        import Path
from ROOT           import RDataFrame
from dmu.pdataframe import utilities as put
from dmu            import LogStore
from rx_common      import Project, Component

from rx_efficiencies           import AcceptanceCalculator
from rx_efficiencies.utilities import is_acceptance_defined

log = LogStore.add_logger('rx_efficiencies:calculate_acceptance')
plt.style.use(mplhep.style.LHCb2)

_RARE_RK     : Final[list[Component]] = [
    Component.bsphiee, 
    Component.bpk1kpipiee, 
    Component.bpk2kpipiee, 
    Component.bpkpee, 
    Component.bpkpmm]
_RARE_RKST   : Final[list[Component]] = [
    Component.bdkstkpiee, 
    Component.bdkstkpimm]
_RESO_RK     : Final[list[Component]] = [
    Component.bpkpjpsiee, 
    Component.bppijpsiee, 
    Component.bpkpjpsimm, 
    Component.bppijpsimm]
_RESO_RKST_EE: Final[list[Component]] = [
    Component.bdkstkpijpsiee, 
    Component.bskstjpsiee, 
    Component.bskstpsi2ee, 
    Component.bsphijpsiee, 
    Component.lbpkjpsiee]
_RESO_RKST_MM: Final[list[Component]] = [
    Component.bdkstkpijpsimm, 
    Component.bskstjpsimm, 
    Component.bskstpsi2mm, 
    Component.bsphijpsimm, 
    Component.lbpkjpsimm]
_GROUPS      : Final[dict[str,list[Component]]] = {
    'Rare $R_K$'              : _RARE_RK,
    'Rare $R_{K^*}$'          : _RARE_RKST,
    'Reso $R_K$'              : _RESO_RK,
    'Reso $R_{K^*}$ electron' : _RESO_RKST_EE,
    'Reso $R_{K^*}$ muon'     : _RESO_RKST_MM,
}
#----------------------------------
class Data:
    '''
    Class used to share data
    '''
    update  : bool
    out_dir : Path 
    version : str
    project : Project

    ana_dir = Path(os.environ['ANADIR'])
    l_energy= ['8TeV', '13TeV', '14TeV']
#----------------------------------
def _get_args():
    parser = argparse.ArgumentParser(description='Used to dump JSON file with acceptances')
    parser.add_argument('-e', '--energy' , nargs='+'    , help='Center of mass energy', default=Data.l_energy, choices=Data.l_energy)
    parser.add_argument('-p', '--project', type =Project, help='E.g. rk or rkst'                                             , required=True) 
    parser.add_argument('-v', '--version', type =str    , help='Version for directory containing JSON files with acceptances', required=True)
    parser.add_argument('-u', '--update' ,                help='If used, will update acceptances, even if found', action = 'store_true')
    args = parser.parse_args()

    Data.l_energy = args.energy
    Data.version  = args.version
    Data.project  = args.project
    Data.update   = args.update
    Data.out_dir  = Data.ana_dir / f'efficiencies/acceptances/{Data.version}/{Data.project}'
    Data.out_dir.mkdir(parents = True, exist_ok=True)
#---------------------------------
def _sample_from_path(path : Path) -> Component:
    '''
    Parameters
    ------------------
    path: Path to ROOT file created with Rapidsim

    Returns
    ------------------
    nickname of decay, e.g. bpkpee
    '''
    filename   = path.name
    identifier = filename.replace('_tree.root', '')

    value = None
    for sample in Component:
        if identifier == sample.name:
            value = sample
            break

    if value is None:
        raise ValueError(f'Cannot recognize {identifier} as a component in: {path}')

    return value 
#----------------------------------
def _get_ntuple_paths(energy : str) -> dict[Component,Path]:
    '''
    Parameters
    --------------------
    energy: Center of mass energy e.g. 7TeV

    Returns
    --------------------
    Dictionary mapping sample with path to ROOT file from RapidSim
    '''
    root_wc = f'Rapidsim/{Data.version}/*/{energy}/*_tree.root'
    l_path  = Data.ana_dir.rglob(pattern=root_wc)

    if not l_path:
        raise FileNotFoundError(f'No files found for: {root_wc} at {energy} in {Data.ana_dir}')

    log.info(f'Picking up files from: {root_wc}')
    d_path  = { _sample_from_path(path=path) : path for path in l_path }

    for sample in d_path:
        log.debug(sample)

    return d_path
#----------------------------------
def _get_acceptances(
    sample : Component, 
    path   : Path, 
    energy : str) -> tuple[float,float]:
    '''
    Parameters
    --------------
    sample : Simulated sample enum
    path   : Path to corresponding Rapidsim ntuple
    energy : Center of mass energy

    Returns
    --------------
    Tuple with physical and LHCb acceptance
    '''
    rdf = RDataFrame('DecayTree', str(path))
    obj = AcceptanceCalculator(
        rdf     = rdf, 
        project = Data.project,
        channel = sample.channel)
    obj.plot_dir     = f'{Data.out_dir}/plots_{energy}/{sample}'
    acc_phy, acc_lhc = obj.get_acceptances()

    return acc_phy, acc_lhc
#----------------------------------
def _load_df(energy : str) -> None | pnd.DataFrame:
    jsn_path = f'{Data.out_dir}/acceptances_{energy}.json'
    if Data.update:
        log.info('Updating acceptances')
        return None

    if not os.path.isfile(jsn_path):
        log.info('Acceptances not found, calculating them')
        return None

    log.warning(f'Using cached acceptances in: {jsn_path}')
    df = pnd.read_json(jsn_path)

    return df
# ----------------------
def _get_df(energy : str) -> pnd.DataFrame:
    df = _load_df(energy = energy)
    if df is not None:
        return df

    d_path = _get_ntuple_paths(energy = energy)
    d_out  = {'Sample' : [], 'Physical' : [], 'LHCb' : []}
    for sample, path in d_path.items():
        if not is_acceptance_defined(sample=sample, project=Data.project):
            continue

        log.debug(f'Checking {sample}')
        acc_phy, acc_lhc = _get_acceptances(
            path    = path, 
            sample  = sample, 
            energy  = energy)

        d_out['Sample'  ].append(sample)
        d_out['Physical'].append(acc_phy)
        d_out['LHCb'    ].append(acc_lhc)

    df = pnd.DataFrame(d_out)

    return df
#----------------------------------
def _save_tables(
    df     : pnd.DataFrame, 
    energy : str) -> None:
    '''
    Saves pandas dataframe as latex table and JSON

    Parameters
    ------------------
    df    : Dataframe with acceptances
    energy: Center of mass energy
    '''
    tex_path = f'{Data.out_dir}/acceptances_{energy}.tex'
    log.info(f'Saving to: {tex_path}')

    df_for_tex = df.assign(Sample=df['Sample'].apply(lambda sample : Component(sample).latex))
    put.df_to_tex(df_for_tex, tex_path, hide_index=True, d_format={'Sample' : '{}', 'Physical' : '{:.3f}', 'LHCb' : '{:.3f}'})

    jsn_path = f'{Data.out_dir}/acceptances_{energy}.json'
    log.info(f'Saving to: {jsn_path}')
    df.to_json(jsn_path, indent=4)
#----------------------------------
def _plot_acceptance(
    df   : pnd.DataFrame, 
    label: str,
    kind : str) -> None:
    '''
    Parameters
    ----------------
    df  : DataFrame with acceptances
    kind: Type of acceptance, e.g. physical
    '''
    _, ax = plt.subplots(figsize=(8,6))
    for process, df_p in df.groupby('Sample'):
        sample = Component(process)

        df_p.plot(x='Energy', y=kind, ax=ax, label=sample.latex, figsize=(12, 8))

    plt.ylim(0.0, 0.20)
    plt.grid()
    plt.title(f'{kind}; {label}')
    plt.ylabel('Acceptance')
    plt.xlabel('')
    plot_path = f'{Data.out_dir}/acceptances_{kind}_{label}.png'
    log.info(f'Saving to: {plot_path}')
    plt.savefig(plot_path)
    plt.close('all')
#----------------------------------
def main():
    '''
    Start here
    '''
    _get_args()
    l_df : list[pnd.DataFrame] = []
    for energy in Data.l_energy:
        df=_get_df(energy)
        _save_tables(df, energy)

        df['Energy'] = energy
        l_df.append(df)

    df = pnd.concat(l_df, axis=0)

    for label, group in _GROUPS.items():
        df_group = df[df['Sample'].isin(group) ]

        _plot_acceptance(df = df_group, kind =     'LHCb', label = label)
        _plot_acceptance(df = df_group, kind = 'Physical', label = label)
#----------------------------------
if __name__ == '__main__':
    main()
