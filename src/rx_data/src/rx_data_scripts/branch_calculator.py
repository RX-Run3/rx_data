'''
Script used to create small trees with extra branches from input trees
'''

import os
import glob
import argparse
import tqdm

from pathlib      import Path
from ROOT         import RDataFrame, TFileMerger, TFile, TTree, RDF # type: ignore
from dmu          import LogLevels, LogStore

from rx_q2        import Q2SmearCorrector
from rx_common    import Component, Project, info
from rx_data      import utilities
from rx_data      import NtuplePartitioner
from rx_data      import MVACalculator
from rx_data      import RDFGetter
from rx_data      import MisCalculator
from rx_data      import HOPCalculator
from rx_data      import SpecMaker
from rx_data      import SWPCalculator
from rx_data      import MassCalculator
from rx_data      import MassBiasCorrector

log = LogStore.add_logger('rx_data:branch_calculator')
# ---------------------------------
class Data:
    '''
    Class used to hold shared data
    '''
    vers : str
    proj : Project 
    kind : str
    nmax : int | None
    part : tuple[int,int]
    pbar : bool
    dry  : bool
    lvl  : int
    wild_card : str | None
    chunk_size: int
    out_dir   : Path 

    l_kind    = ['mass', 'hop', 'swp_jpsi_misid', 'swp_cascade', 'brem_track_2', 'mva', 'smear']
    tree_name = 'DecayTree'
    ana_dir   = Path(os.environ['ANADIR'])
# ---------------------------------
def _parse_args() -> None:
    '''
    Parse arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to create ROOT files with trees with extra branches by picking up inputs from directory and patitioning them')
    parser.add_argument('-k', '--kind', type=str, help='Kind of branch to create', choices=Data.l_kind, required=True)
    parser.add_argument('-P', '--proj', type=str, help='Project'                 , choices=['rk', 'rkst', 'rk_nopid', 'rkst_nopid', 'rk_no_refit'], required=True)
    parser.add_argument('-v', '--vers', type=str, help='Version of outputs', required=True)
    parser.add_argument('-w', '--wc'  , type=str, help='Wildcard, if passed will be used to match paths')
    parser.add_argument('-n', '--nmax', type=int, help='If used, limit number of entries to process to this value')
    parser.add_argument('-s', '--chunk',type=int, help='It will set the number of entries the dataframes will be split on before processing', default=100_000)
    parser.add_argument('-p', '--part', nargs= 2, help='Partitioning, first number is the index, second is the number of parts', required=True)
    parser.add_argument('-b', '--pbar',           help='If used, will show progress bar whenever it is available', action='store_true')
    parser.add_argument('-d', '--dry' ,           help='If used, will do dry drun, e.g. stop before processing', action='store_true')
    parser.add_argument('-l', '--lvl' , type=int, help='log level', choices=[5, 10, 20, 30], default=20)
    args = parser.parse_args()

    igroup, ngroup = args.part
    igroup    = int(igroup)
    ngroup    = int(ngroup)

    Data.kind = args.kind
    Data.proj = args.proj
    Data.vers = args.vers
    Data.part = igroup, ngroup 
    Data.nmax = args.nmax
    Data.pbar = args.pbar
    Data.dry  = args.dry
    Data.lvl  = args.lvl
    Data.wild_card = args.wc
    Data.chunk_size= args.chunk
# ---------------------------------
def _set_logs():
    '''
    This method will set the logging level of multiple tools
    '''
    LogStore.set_level('rx_data:branch_calculator'  , Data.lvl)
    LogStore.set_level('rx_data:mass_calculator'    , Data.lvl)
    LogStore.set_level('rx_data:mva_calculator'     , Data.lvl)
    LogStore.set_level('rx_data:mis_calculator'     , Data.lvl)
    LogStore.set_level('rx_data:swp_calculator'     , Data.lvl)
    LogStore.set_level('rx_data:hop_calculator'     , Data.lvl)
    LogStore.set_level('dmu:ml:cv_predict'          , Data.lvl)
    LogStore.set_level('dmu:ml:CVClassifier'        , Data.lvl)

    LogStore.set_level('rx_data:mass_bias_corrector',       30)
    LogStore.set_level('rx_data:photon_veto'        ,       30)
    LogStore.set_level('rx_data:path_splitter'      ,       30)
    LogStore.set_level('rx_data:rdf_getter'         ,       30)
    LogStore.set_level('rx_data:sample_emulator'    ,       30)
    LogStore.set_level('rx_data:sample_patcher'     ,       30)
    LogStore.set_level('rx_data:spec_maker'         ,       30)

    if Data.lvl < LogLevels.info:
        LogStore.set_level('rx_data:spec_maker', Data.lvl)
        LogStore.set_level('rx_data:rdf_getter', Data.lvl)
# ---------------------------------
def _get_out_dir() -> Path:
    '''
    Returns
    -------------
    Path to directory where output ROOT files will be stored
    '''
    out_dir  = Data.ana_dir / f'Data/{Data.proj}/{Data.kind}/{Data.vers}'

    if not Data.dry:
        out_dir.mkdir(parents=True, exist_ok=True)

    return out_dir
# ---------------------------------
def _get_out_path(path : Path) -> str:
    fname    = os.path.basename(path)
    out_path = f'{Data.out_dir}/{fname}'

    log.debug(f'Creating : {out_path}')

    return out_path
# ---------------------------------
def _process_rdf(
    rdf     : RDF.RNode,
    path    : Path) -> RDF.RNode|None:
    '''
    Takes:

    rdf : Dataframe to have the columns added
    path: Full path to corresponding ROOT file

    Returns:
    Either:
    - Dataframe with columns needed
    - None, in case it does not make sense to add the columns to this type of file
    '''
    mc_sample, trigger = utilities.info_from_path(path=path, sample_lowercase=False)
    component = Component.from_sample(sample = mc_sample)

    nentries = rdf.Count().GetValue()
    if nentries == 0:
        log.warning(f'Found empty input file: {path}/{Data.tree_name}')
        rdf=RDataFrame(0)
        rdf=rdf.Define('fake_column', '1')

        return rdf
    else:
        log.debug(30 * '-')
        log.debug(f'Found {nentries} entries in: {path}')
        log.debug(30 * '-')

    msc = MisCalculator(rdf=rdf, trigger=trigger)
    rdf = msc.get_rdf()

    if   Data.kind == 'hop':
        obj = HOPCalculator(rdf=rdf, trigger=trigger)
        rdf = obj.get_rdf(preffix=Data.kind)
    elif Data.kind == 'brem_track_2':
        df   = utilities.df_from_rdf(rdf=rdf, drop_nans=False)
        is_mc= utilities.rdf_is_mc(rdf=rdf)
        cor  = MassBiasCorrector(
            df                 = df, 
            is_mc              = is_mc,
            trigger            = trigger,
            ecorr_kind         = Data.kind,
            photon_veto_version= 'v1')

        df  = cor.get_df(suffix=Data.kind)
        rdf = RDF.FromPandas(df)
    elif Data.kind in ['swp_cascade', 'swp_jpsi_misid']:
        rdf = _get_swap_rdf(rdf=rdf, trigger=trigger)
    elif Data.kind == 'smear':
        rdf = _get_smear_rdf(rdf=rdf, trigger=trigger)
    elif Data.kind == 'mva'   :
        obj = MVACalculator(rdf=rdf, sample=component, trigger=trigger, version=Data.vers)
        rdf = obj.get_rdf(kind = 'root')
    elif Data.kind == 'mass':
        obj = MassCalculator(rdf=rdf)
        rdf = obj.get_rdf()
    else:
        raise ValueError(f'Invalid kind: {Data.kind}')

    return rdf
# ----------------------
def _get_smear_rdf(rdf : RDF.RNode, trigger : str) -> RDF.RNode:
    '''
    Parameters
    -------------
    rdf    : ROOT dataframe
    trigger: HLT2 trigger

    Returns
    -------------
    ROOT dataframe with smeared masses
    '''

    channel = info.channel_from_trigger(trigger=trigger)
    obj     = Q2SmearCorrector(channel=channel.lower())
    rdf     = obj.get_rdf(rdf=rdf)

    return rdf
# ----------------------
def _get_swap_rdf(rdf : RDF.RNode, trigger : str) -> RDF.RNode:
    '''
    Parameters
    -------------
    rdf    : ROOT dataframe
    trigger: HLT2 trigger

    Returns
    -------------
    ROOT dataframe with the swap masses
    '''
    # TODO: Remove the SS condition for the SWPCalculator
    # When the data ntuples with fixed descriptor be ready
    is_ss   = 'SameSign' in trigger
    lep_id  = 11 if info.is_ee(trigger=trigger) else 13
    project = info.project_from_trigger(trigger=trigger, lower_case=True)

    log.info(f'Found project {project} for trigger {trigger}')

    # Pion is the one that gets misidentified as electron
    # pi(-> e/mu) + e/mu combinations
    kaon_name = {'rk' : 'H', 'rkst' : 'H2'}[project]
    if Data.kind == 'swp_jpsi_misid':
        obj = SWPCalculator(rdf=rdf, d_lep={'L1' : lep_id, 'L2' : lep_id}, d_had={kaon_name : lep_id})
        rdf = obj.get_rdf(preffix=Data.kind, progress_bar=Data.pbar, use_ss=is_ss)

        return rdf

    # These are Kpi combinations
    kaon_name = {'rk' : 'H', 'rkst' : 'H1'}[project]
    if Data.kind == 'swp_cascade':
        obj = SWPCalculator(rdf=rdf, d_lep={'L1' : 211, 'L2' : 211}, d_had={kaon_name : 321})
        rdf = obj.get_rdf(preffix=Data.kind, progress_bar=Data.pbar, use_ss=is_ss)

        return rdf

    raise ValueError(f'Invalid kind: {Data.kind}')
# ---------------------------------
def _split_rdf(rdf : RDF.RNode) -> list[RDF.RNode]:
    nentries = rdf.Count().GetValue()
    l_size   = range(0, nentries, Data.chunk_size)

    l_rdf    = [
        rdf.Range(start, min(start + Data.chunk_size, nentries))
        for start in l_size ]

    return l_rdf
# ----------------------
def _get_input_rdf(path : Path) -> RDF.RNode:
    '''
    Parameters
    -------------
    path: Path to ROOT file

    Returns
    -------------
    ROOT dataframe associated
    '''
    mc_sample, trigger = utilities.info_from_path(path=path, sample_lowercase=False)
    component = Component.from_sample(sample = mc_sample)

    s_friend : set[str] = set()
    if Data.kind == 'mva':
        s_friend = {'brem_track_2', 'hop', 'smear'}

    if Data.kind == 'smear':
        s_friend = {'brem_track_2'}

    with RDFGetter.only_friends(s_friend=s_friend),\
         SpecMaker.project(project = Data.proj):
        gtr   = RDFGetter(sample=component, trigger=trigger)
        d_rdf = gtr.get_rdf(per_file=True)

    rdf = d_rdf.get(path)
    if rdf is None:
        for path_found in d_rdf:
            log.info(path_found)
        raise ValueError(f'Cannot find dataframe for: {path}')

    if Data.nmax is not None:
        rdf=rdf.Range(Data.nmax)

    return rdf
# ---------------------------------
def _create_file(path : Path) -> None:
    '''
    Parameters
    ------------------
    path : ROOT file path
    '''
    out_path = _get_out_path(path)
    if os.path.isfile(out_path):
        log.debug(f'Output found, skipping {out_path}')
        return

    rdf   = _get_input_rdf(path=path)
    nentries = rdf.Count().GetValue()
    if nentries == 0:
        log.warning(f'Found empty dataframe for: {path}')
        log.info(f'Saving empty output to: {out_path}')

        ofile=TFile(out_path, 'recreate')
        ttree=TTree('DecayTree', '')
        ttree.Write()
        ofile.Close()

        return

    l_rdf = _split_rdf(rdf=rdf)

    if Data.dry:
        log.debug('Doing dry run')
        return

    nchunk = len(l_rdf)
    if nchunk == 1:
        log.info('File will be processed in a single chunk')
        rdf = l_rdf[0]
        rdf = _process_rdf(rdf, path)
        if rdf is not None:
            rdf.Snapshot(Data.tree_name, out_path)

        return

    _process_and_merge(
        l_rdf     = l_rdf,
        input_path= path,
        out_path  = out_path,
        nchunk    = nchunk)

    tmp_wc = out_path.replace('.root', '_*_pre_merge.root')
    log.info(f'Removing temporary files from: {tmp_wc}')
    for tmp_path in glob.glob(tmp_wc):
        os.remove(tmp_path)
# ----------------------
def _process_and_merge(
    l_rdf     : list[RDF.RNode],
    nchunk    : int,
    out_path  : str,
    input_path: Path) -> None:
    '''
    Parameters
    -------------
    l_rdf   : List of ROOT dataframes
    nchunk  : Number of chunks into which the dataframe was processed
    out_path: Path to output file
    path    : Path to merged ROOT output file
    '''
    log.info(f'File will be processed in {nchunk} chunks')
    fmrg = TFileMerger()
    for index, rdf_in in enumerate(tqdm.tqdm(l_rdf, ascii=' -')):
        rdf_out  = _process_rdf(rdf_in, input_path)
        if rdf_out is None:
            continue

        tmp_path = out_path.replace('.root', f'_{index:03}_pre_merge.root')

        log.debug(f'Saving tree {Data.tree_name} to {tmp_path}')
        rdf_out.Snapshot(Data.tree_name, tmp_path)

        fmrg.AddFile(tmp_path, cpProgress=False)

    fmrg.OutputFile(out_path)

    log.info(f'Merging temporary files into: {out_path}')
    fmrg.Merge()
# ----------------------
def main():
    '''
    Entry point

    Parameters
    ---------------------
    args: Arguments needed to start calculation when used as module, 
          If not passed, this will be used as an script
    '''
    _parse_args()
    _set_logs()

    prt = NtuplePartitioner(
        kind      = 'main',
        project   = Data.proj,
        wild_card = Data.wild_card)

    igroup, ngroup = Data.part
    l_path = prt.get_paths(index=igroup, total=ngroup)

    Data.out_dir = _get_out_dir()

    log.info('Processing paths')

    if Data.dry:
        log.warning('This is a dry run')

    if isinstance(Data.nmax, int):
        log.info(f'Limitting dataframe to {Data.nmax} entries')

    for path in tqdm.tqdm(l_path, ascii=' -'):
        log.debug(f'{"":<4}{path}')
        _create_file(path=path)
# ---------------------------------
if __name__ == '__main__':
    main()
