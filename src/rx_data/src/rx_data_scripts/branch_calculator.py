'''
Script used to create small trees with extra branches from input trees
'''
import os
import tqdm
import argparse

from typing       import Final
from pydantic     import BaseModel
from pathlib      import Path
from ROOT         import TFile, TTree, RDF
from dmu          import LogStore, LogLevels
from dmu.generic  import Mode
from rx_q2        import Q2SmearCorrector
from rx_common    import Component, Project, Trigger, MissingComponent
from rx_data      import utilities
from rx_data      import MVACalculator
from rx_data      import RDFGetter
from rx_data      import MisCalculator
from rx_data      import HOPCalculator
from rx_data      import SpecMaker
from rx_data      import SWPCalculator
from rx_data      import MassCalculator
from rx_data      import MassBiasCorrector
from rx_data      import FilePart, SampleSplitter

log                       = LogStore.add_logger('rx_data:branch_calculator')
_ANADIR     : Final[Path] = Path(os.environ['ANADIR'])
_KINDS : Final[list[str]] = ['mass', 'hop', 'swp_jpsi_misid', 'swp_cascade', 'brem_track_2', 'mva', 'smear']
_TREE_NAME : Final[str]   = 'DecayTree'
# ---------------------------------
class Config(BaseModel):
    '''
    Class used to hold shared data
    '''
    photon_veto : str
    vmain       : str
    vfrnd       : str
    proj        : Project
    kind        : str
    pbar        : bool
    dry         : bool
    lvl         : int
    entries     : int
    index       : int
# ---------------------------------
def _parse_args() -> Config:
    '''
    Parse arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to create ROOT files with trees with extra branches by picking up inputs from directory and patitioning them')
    parser.add_argument('-g', '--photon_veto', type=str, help='Version of photon veto, default no veto'  , default='v0')
    parser.add_argument('-k', '--kind'       , type=str, help='Kind of branch to create', choices=_KINDS, required=True)
    parser.add_argument('-p', '--proj'       , type=str, help='Project'                 , choices=Project, required=True)
    parser.add_argument('-M', '--vmain'      , type=str, help='Version of main tree'    , required=True)
    parser.add_argument('-F', '--vfrnd'      , type=str, help='Version of friend trees' , required=True)
    parser.add_argument('-i', '--index'      , type=int, help='Index of batch of file parts to use in calculation', required = True)
    parser.add_argument('-e', '--entries'    , type=int, help='Number of entries to split dataset into', required = True)
    parser.add_argument('-l', '--lvl'        , type=int, help='log level', choices=LogLevels, default=20)
    parser.add_argument('-b', '--pbar'       ,           help='If used, will show progress bar whenever it is available', action='store_true')
    parser.add_argument('-d', '--dry'        ,           help='If used, will do dry drun, e.g. stop before processing', action='store_true')
    args = parser.parse_args()

    cfg = Config(
        photon_veto = args.photon_veto,
        kind        = args.kind,
        proj        = args.proj,
        vmain       = args.vmain,
        vfrnd       = args.vfrnd,
        pbar        = args.pbar,
        dry         = args.dry,
        index       = args.index,
        entries     = args.entries,
        lvl         = args.lvl)

    return cfg
# ---------------------------------
def _set_logs(cfg : Config):
    '''
    This method will set the logging level of multiple tools
    '''
    LogStore.set_level('rx_data:sample_splitter'    , cfg.lvl)
    LogStore.set_level('rx_data:branch_calculator'  , cfg.lvl)
    LogStore.set_level('rx_data:mass_calculator'    , cfg.lvl)
    LogStore.set_level('rx_data:mva_calculator'     , cfg.lvl)
    LogStore.set_level('rx_data:mis_calculator'     , cfg.lvl)
    LogStore.set_level('rx_data:swp_calculator'     , cfg.lvl)
    LogStore.set_level('rx_data:hop_calculator'     , cfg.lvl)
    LogStore.set_level('dmu:ml:cv_predict'          , cfg.lvl)
    LogStore.set_level('dmu:ml:CVClassifier'        , cfg.lvl)

    LogStore.set_level('rx_data:mass_bias_corrector',      30)
    LogStore.set_level('rx_data:photon_veto'        ,      30)
    LogStore.set_level('rx_data:path_splitter'      ,      30)
    LogStore.set_level('rx_data:rdf_getter'         ,      30)
    LogStore.set_level('rx_data:sample_emulator'    ,      30)
    LogStore.set_level('rx_data:sample_patcher'     ,      30)
    LogStore.set_level('rx_data:spec_maker'         ,      30)
# ---------------------------------
def _process_rdf(
    rdf : RDF.RNode,
    cfg : Config,
    path: Path) -> RDF.RNode:
    '''
    Parameters
    --------------
    rdf : Non-empty dataframe to have the columns added
    cfg : Configuration
    path: Full path to corresponding ROOT file

    Returns:
    --------------
    Dataframe with columns needed
    '''
    mc_sample, trigger = utilities.info_from_path(path=path, sample_lowercase=False)

    component = Component.from_sample(sample = mc_sample)
    nentries  = rdf.Count().GetValue()
    log.debug(30 * '-')
    log.debug(f'Found {nentries} entries in: {path}')
    log.debug(30 * '-')

    msc = MisCalculator(rdf=rdf, trigger=trigger)
    rdf = msc.get_rdf()

    if   cfg.kind == 'hop':
        obj = HOPCalculator(rdf=rdf, trigger=trigger)
        rdf = obj.get_rdf(preffix=cfg.kind)
    elif cfg.kind == 'brem_track_2':
        df   = utilities.df_from_rdf(rdf=rdf, drop_nans=False)
        is_mc= utilities.rdf_is_mc(rdf=rdf)
        cor  = MassBiasCorrector(
            df                 = df,
            is_mc              = is_mc,
            trigger            = trigger,
            ecorr_kind         = cfg.kind,
            photon_veto_version= cfg.photon_veto)

        df  = cor.get_df(suffix=cfg.kind)
        rdf = RDF.FromPandas(df)
    elif cfg.kind in ['swp_cascade', 'swp_jpsi_misid']:
        rdf = _get_swap_rdf(rdf=rdf, trigger=trigger, cfg = cfg)
    elif cfg.kind == 'smear':
        obj = Q2SmearCorrector(channel=trigger.channel)
        rdf = obj.get_rdf(rdf=rdf)
    elif cfg.kind == 'mva'   :
        obj = MVACalculator(rdf=rdf, sample=component, trigger=trigger, version=cfg.vfrnd)
        rdf = obj.get_rdf(kind = 'root')
    elif cfg.kind == 'mass':
        obj = MassCalculator(rdf=rdf)
        rdf = obj.get_rdf()
    else:
        raise ValueError(f'Invalid kind: {cfg.kind}')

    return rdf
# ----------------------
def _get_swap_rdf(
    rdf     : RDF.RNode,
    cfg     : Config,
    trigger : Trigger) -> RDF.RNode:
    '''
    Parameters
    -------------
    rdf    : ROOT dataframe
    cfg    : Config object
    trigger: HLT2 trigger

    Returns
    -------------
    ROOT dataframe with the swap masses
    '''
    lep_id  = 11 if trigger.is_electron else 13
    project = trigger.project

    log.info(f'Found project {project} for trigger {trigger}')

    # Pion is the one that gets misidentified as electron
    # pi(-> e/mu) + e/mu combinations
    kaon_name = {'rk' : 'H', 'rkst' : 'H2'}[project]
    if cfg.kind == 'swp_jpsi_misid':
        obj = SWPCalculator(rdf=rdf, d_lep={'L1' : lep_id, 'L2' : lep_id}, d_had={kaon_name : lep_id})
        rdf = obj.get_rdf(preffix=cfg.kind, progress_bar=cfg.pbar, use_ss=trigger.is_ss)

        return rdf

    # These are Kpi combinations
    kaon_name = {'rk' : 'H', 'rkst' : 'H1'}[project]
    if cfg.kind == 'swp_cascade':
        obj = SWPCalculator(rdf=rdf, d_lep={'L1' : 211, 'L2' : 211}, d_had={kaon_name : 321})
        rdf = obj.get_rdf(preffix=cfg.kind, progress_bar=cfg.pbar, use_ss=trigger.is_ss)

        return rdf

    raise ValueError(f'Invalid kind: {cfg.kind}')
# ---------------------------------
def _get_input_rdf(
    cfg  : Config,
    path : Path) -> RDF.RNode:
    '''
    Parameters
    -------------
    cfg : Configuration object
    path: Path to ROOT file

    Returns
    -------------
    ROOT dataframe associated
    '''
    sample, trigger = utilities.info_from_path(path=path, sample_lowercase=False)
    component = Component.from_sample(sample = sample)

    s_friend : set[str] = set()
    if cfg.kind == 'mva':
        s_friend = {'brem_track_2', 'hop', 'smear'}

    if cfg.kind == 'smear':
        s_friend = {'brem_track_2'}

    with RDFGetter.only_friends(s_friend=s_friend),\
         SpecMaker.project(project = cfg.proj):
        gtr   = RDFGetter(sample=component, trigger=trigger)
        d_rdf = gtr.get_rdf(per_file=True)

    rdf = d_rdf.get(path)
    if rdf is None:
        for path_found in d_rdf:
            log.info(path_found)
        raise ValueError(f'Cannot find dataframe for: {path}')

    return rdf
# ---------------------------------
def _skip_file(input_path : Path, output_path : Path) -> bool:
    '''
    Parameters
    ----------------
    input : Path to input ROOT file from main category
    output: Path to output friend tree file

    Returns
    ----------------
    True, if output exists and is newer than input, false otherwise.
    '''
    if not output_path.exists():
        log.debug(f'Creating: {output_path}')
        return False

    is_stale = input_path.stat().st_mtime > output_path.stat().st_mtime

    if is_stale:
        log.debug(f'Stale friend, processing: {input_path}')
        return False

    log.debug(f'Skipping, friend found: {output_path}')

    return True
# ---------------------------------
def _create_file(
    cfg  : Config,
    part : FilePart) -> None:
    '''
    Parameters
    ------------------
    cfg : Object holding configuration
    part: ROOT file part
    '''
    output_path = part.friend_path(friend = cfg.kind, version = cfg.vfrnd)
    if _skip_file(input_path = part.path, output_path = output_path):
        return

    try:
        rdf = _get_input_rdf(path=part.path, cfg = cfg)
    except MissingComponent as exc:
        log.warning(f'Not processing: {part.path}. Reason {exc}', exc_info = False)
        return

    nentries = rdf.Count().GetValue()
    if nentries == 0:
        log.warning(f'Found empty dataframe for: {part.path}')
        log.info(f'Saving empty output to: {output_path}')

        ofile=TFile(str(output_path), 'recreate')
        ttree=TTree('DecayTree', '')
        ttree.Write()
        ofile.Close()

        return

    lo, hi = part.range
    if part.split:
        rdf = rdf.Filter(f'rdfentry_ >= {lo} && rdfentry_ <= {hi}')

    if cfg.dry:
        log.debug('Doing dry run')
        return

    output_part_path = part.friend_part_path(friend = cfg.kind, version = cfg.vfrnd)
    if output_part_path.exists():
        return

    rdf = _process_rdf(
        rdf = rdf,
        cfg = cfg,
        path= part.path)

    log.debug(f'Saving file to {output_path}')
    output_part_path.parent.mkdir(exist_ok=True, parents=True)
    rdf.Snapshot(_TREE_NAME, str(output_part_path))
# ----------------------
def main():
    '''
    Entry point

    Parameters
    ---------------------
    args: Arguments needed to start calculation when used as module,
          If not passed, this will be used as an script
    '''
    cfg = _parse_args()
    _set_logs(cfg = cfg)
    out_path = _ANADIR / f'DB/statistics/{cfg.vmain}/{cfg.proj}.json'

    spt   = SampleSplitter(
        version = cfg.vmain,
        project = cfg.proj)
    files = spt.run(out_path = out_path, mode = Mode.read)

    batches = files.split(entries = cfg.entries)
    batch   = batches.at(cfg.index)

    log.info('Processing paths')

    if cfg.dry:
        log.warning('This is a dry run')

    for file_part in tqdm.tqdm(batch.root, ascii=' -'):
        _create_file(
            cfg  = cfg,
            part = file_part)
# ---------------------------------
if __name__ == '__main__':
    main()
