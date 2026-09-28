'''
Module containing the selection function, which returns a dictionary of cuts
'''

import copy
import yaml

from functools              import cache
from pathlib                import Path
from contextlib             import contextmanager
from importlib.resources    import files
from ROOT                   import RDF # type: ignore
from dmu                    import LogStore
from dmu.generic            import hashing
from dmu.rdataframe         import utilities          as rut
from dmu.generic            import utilities          as gut
from rx_selection           import truth_matching     as tm
from rx_common              import Channel, Component, Project, Qsq, Trigger, Cuts

log=LogStore.add_logger('rx_selection:selection')
#-----------------------
class Data:
    '''
    Class used to store share attributes
    '''
    l_project  = ['RK', 'RKst']
    l_analysis = ['EE', 'MM'  ]
    l_q2bin    = ['low', 'central', 'jpsi', 'psi2S', 'high']

    d_custom_selection : None | dict[Cuts,str] = None
#-----------------------
class MultipleSelectionOverriding(Exception):
    '''
    Will be risen when global selection is overriden more than once per run
    '''
    def __init__(self, message : str):
        super().__init__(message)
#-----------------------
@contextmanager
def custom_selection(
    d_sel          : dict[Cuts, str] | None,
    force_override : bool = False):
    '''
    This is a context manager updates the **default** selection

    Parameters
    ------------------
    d_sel: Dictionary with
        - key  : Name of cut, e.g. brem
        - value: Definition of cut, e.g. nbrem > 0
        If dictionary is None, will not touch the selection
        If dictionary is empty, will return default (not overriden) selection, if force_override=True

    force_override: If False (default) will raise exception if manager has been called already
                    This should prevent multiple selections to be used accidentally.
                    However user will have to explicitly force override when this behaviour
                    is intended
    '''
    if d_sel is None:
        yield
        return

    if not force_override and Data.d_custom_selection is not None:
        log.error(yaml.dump(d_sel))
        raise MultipleSelectionOverriding('Custom selection already set, cannot set it twice')

    org_val = Data.d_custom_selection
    Data.d_custom_selection = d_sel

    try:
        yield
    finally:
        Data.d_custom_selection = org_val
# ----------------------
@contextmanager
def update_selection(d_sel : dict[Cuts,str]):
    '''
    This manager will update **current** selection, i.e. whatever is the selection up to
    the moment the manager is used

    Parameters
    -------------
    d_sel: Selection that will be used to update custom + default selection
    '''
    org_val = None if Data.d_custom_selection is None else copy.deepcopy(Data.d_custom_selection)

    if Data.d_custom_selection is None:
        Data.d_custom_selection = {}

    Data.d_custom_selection.update(d_sel)

    try:
        yield
    finally:
        Data.d_custom_selection = org_val
#-----------------------
def _print_selection(d_cut : dict[Cuts,str]) -> None:
    for name, expr in d_cut.items():
        log.debug(f'{name:<20}{expr}')
#-----------------------
def selection(
    q2bin     : Qsq,
    process   : Component,
    trigger   : Trigger,
    skip_truth: bool = False,
    smeared   : bool = True) -> dict[Cuts,str]:
    '''
    Picks up sample name, trigger, etc, returns dictionary with selection

    q2bin     : low, central, jpsi, psi2S or high
    process   : Nickname for MC sample, starts with "DATA" for data
    smeared   : If true (default), the selection will use cuts on smeared masses. Only makes sense for electron MC samples
    trigger   : E.g. Hlt2RD...
    skip_truth: By default False, if True, it will not include truth matching requirement
    '''
    if 'toy' in process:
        log.warning(f'Process {process} recognized as toy sample, returning empty selection')
        return {}

    d_cut : dict[Cuts,str] = {}

    event_type = process if not process.is_mc else process.event_type
    log.info(f'{process:<40}{"->":20}{event_type:<20}')

    if not process.is_mc:
        log.debug('Adding cleaning requirement for data')
        d_cut[Cuts.clean] = 'dataq == 1'
        d_cut[Cuts.block] = 'block >= 1'
    elif skip_truth:
        log.warning('Not using truth matching')
        d_cut[Cuts.truth] = '(1)'
    else:
        log.debug('Adding truth matching requirement for MC')
        d_cut[Cuts.truth] = tm.get_truth(component=process, project = trigger.project)

    d_tmp = _get_selection(
        chan   = trigger.channel,
        proj   = trigger.project,
        q2_bin = q2bin)
    d_cut.update(d_tmp)

    if Data.d_custom_selection is not None:
        try:
            d_cut.update(Data.d_custom_selection)
        except ValueError as exc:
            log.error(yaml.dump(Data.d_custom_selection))
            raise ValueError('Cannot update selection') from exc

    d_cut = _update_mass_cuts(
        d_cut   =   d_cut,
        q2bin   =   q2bin,
        sample  = process,
        trigger = trigger,
        smeared = smeared)

    _print_selection(d_cut)

    return d_cut
# ----------------------
def get_q2_cut(q2bin : Qsq) -> str:
    '''
    Parameters
    -------------
    q2bin: E.g. central

    Returns
    -------------
    Cut defining q2bin
    '''
    data = _load_selection_config()
    q2sel= data['q2_common']
    val  = q2sel[q2bin]

    if not isinstance(val, str):
        raise ValueError(f'q2 cut not a string: {val}')

    return val
#-----------------------
def _update_mass_cuts(
    d_cut   : dict[Cuts,str],
    q2bin   : Qsq,
    sample  : Component,
    trigger : Trigger,
    smeared : bool) -> dict[Cuts,str]:
    '''
    Parameters
    ---------------
    d_cut   : Dictionary with cuts
    q2bin   : E.g. central
    sample  : Sample to which selection will be applied
    trigger : Hlt2 trigger
    sameared: If true, override masses and q2 with the smeared version, whenever it makes sense; e.g. not for data
    '''
    should_smear = sample.is_mc and trigger.is_electron

    if not should_smear:
        log.debug(f'Not using cuts on smeared masses for {sample}/{trigger}')
        return d_cut

    if not smeared:
        log.warning('Using cuts on un-smeared masses')
        return d_cut

    log.debug('Using cuts on smeared masses')
    d_cut = _use_smeared_masses(cuts=d_cut, q2bin=q2bin)

    return d_cut
#-----------------------
def _use_smeared_masses(
    cuts  : dict[Cuts,str],
    q2bin : Qsq) -> dict[Cuts,str]:
    '''
    Parameters
    -------------
    cuts : Selection cuts
    q2bin: E.g. central

    Returns
    -------------
    Dictionary of cuts with q2 and mass cuts updated
    to use smeared values or not
    '''
    log.info('Overriding selection for electron MC to use smeared q2 and mass')

    cut_org = cuts[Cuts.q2]
    if 'q2_track' not in cut_org:
        cut_new       = cut_org.replace('q2', 'q2_smr')
        cuts[Cuts.q2] = cut_new

        log.debug('Overriding:')
        log.debug(cut_org)
        log.debug('--->')
        log.debug(cut_new)
    else:
        # TODO: IF we use the q2_track for this cut, we need to find the
        # correct smearing factors here
        log.warning(f'Not overriding with smeared version q2 cut: {cut_org}')

    if not q2bin.is_rare:
        log.debug(f'Not overriding mass cut for resonant bin: {q2bin}')
        return cuts

    cut_org = cuts[Cuts.mass]
    cut_new = cut_org.replace('B_Mass', 'B_Mass_smr')
    cuts[Cuts.mass] = cut_new

    log.debug('Overriding:')
    log.debug(cut_org)
    log.debug('--->')
    log.debug(cut_new)

    return cuts
#-----------------------
@cache
def _load_selection_config() -> dict[str,dict[str,str | dict[str,str]]]:
    '''
    Returns dictionary with the latest selection config
    '''
    path = files('rx_selection_data').joinpath('selection/latest.yaml')
    path = str(path)
    log.info(f'Loading selection from: {path}')

    with open(path, encoding='utf-8') as ifile:
        d_sel = yaml.safe_load(ifile)

    return d_sel
#-----------------------
# TODO: Add types
def _get_selection(
    chan   : Channel,
    proj   : Project,
    q2_bin : Qsq) -> dict[str,str]:
    '''
    Parameters
    -----------------
    chan  : Channel, e.g. EE, MM
    proj  : Project, e.g. RK, RKst
    q2_bin: q2 bin e.g. central, needed to pick for q2 dependent cuts

    Returns
    -----------------
    Dictionary with:

    key  : Label of cut, e.g. q2
    value: Cut expression e.g. q2 > 1e6
    '''
    cfg = _load_selection_config()

    if proj not in cfg:
        for key in cfg:
            log.error(key)
        raise ValueError(f'Cannot find {proj} in config')

    if chan not in cfg[proj]:
        raise ValueError(f'Cannot find {chan} in config section for {proj}')

    d_cut = cfg[proj][chan]
    if isinstance(d_cut, str):
        raise ValueError(f'Selection at {proj}/{chan} is a string: {d_cut}')

    d_new = {}
    for cut_name, d_q2bin in d_cut.items():
        if not isinstance(d_q2bin, dict):
            d_new[cut_name] = d_q2bin
            continue

        if q2_bin not in d_q2bin:
            for val in d_q2bin:
                log.error(val)

            raise ValueError(f'Cannot find q2 bin {q2_bin} in {cut_name} section')

        cut_val = d_q2bin[q2_bin]
        log.debug(f'Overriding {cut_name} for {q2_bin}')

        d_new[cut_name] = cut_val

    return d_new
#-----------------------
def _save_cutflow(
    path : Path,
    rdf  : RDF.RNode,
    cuts : dict[Cuts,str]) -> None:
    '''
    Parameters
    -------------
    path: Path where cutflow will be saved
    rdf : Root Dataframe
    cuts: Selection
    '''
    path.mkdir(parents=True, exist_ok=True)

    rep = rdf.Report()
    df  = rut.rdf_report_to_df(rep=rep)

    cf_path = path / 'cutflow.md'
    log.info(f'Saving cutflow to: {cf_path}')
    df.to_markdown(cf_path)

    ct_path = path / 'cuts.json'
    log.info(f'Saving cuts to: {ct_path}')
    gut.dump_json(data = cuts, path = ct_path, exists_ok=True)
#-----------------------
def apply_full_selection(
    rdf      : RDF.RNode,
    q2bin    : Qsq,
    process  : Component,
    trigger  : Trigger,
    ext_cut  : str |None     = None,
    uid      : str |None     = None,
    out_path : Path|None|int = None) -> RDF.RNode:
    '''
    Will apply full selection on dataframe.
    IMPORTANT: This HAS to be done lazily or else the rest of the code will be slowed down.

    Parameters
    --------------------
    uid     : Unique identifier, used for hashing. If not passed no hashing will be done
    ext_cut : Extra cut, optional
    out_path: Either:
        - Directory path where selection and cutflow will be stored, optional
        - None if no argument was passed, default. Will show warning about missing path
        - Integer, e.g. 0, if one does not want to save cutflow. For example, to keep this as lazy execution

    Returns
    --------------------
    Dataframe after full selection.
    If uid was passed, the uid will be recalculated and attached to the dataframe.
    '''

    d_sel = selection(
        q2bin  =q2bin,
        process=process,
        trigger=trigger)

    if ext_cut is not None:
        d_sel[Cuts.extra] = ext_cut

    log.info(60 * '-')
    log.info('Applying cuts')
    log.info(60 * '-')
    for cut_name, cut_value in d_sel.items():
        log.debug(f'{cut_name:<40}{cut_value}')
        try:
            rdf = rdf.Filter(cut_value, cut_name)
        except Exception as exc:
            raise ValueError(f'Cannot apply cut \"{cut_name}\" -> \"{cut_value}\"') from exc

    if isinstance(out_path, Path):
        _save_cutflow(path=out_path, rdf=rdf, cuts=d_sel)
    elif out_path is None:
        log.warning('Not saving cutflow')
    else:
        log.debug('Not saving cutflow, as explicitly requested')
        pass

    if uid is None:
        log.debug('No UID found, not updating it')
        return rdf

    log.info('Attaching updated UID and selection to dataframe')
    uid = hashing.hash_object([uid, d_sel])
    setattr(rdf, 'uid',   uid) # noqa: B010
    setattr(rdf, 'sel', d_sel) # noqa: B010

    return rdf
# ----------------------
def apply_selection(
    rdf      : RDF.RNode,
    cuts     : dict[Cuts,str],
    out_path : Path | None,
    uid      : str  | None = None) -> RDF.RNode:
    '''
    Will apply selection on dataframe.
    IMPORTANT: This HAS to be done lazily or else the rest of the code will be slowed down.

    Parameters
    --------------------
    rdf     : ROOT DataFrame
    cuts    : Dictionary mapping cut label with expression
    uid     : String symbolizing unique identifier for input dataframe
    out_path: Directory path where selection and cutflow will be stored.
              None for not saving selection.

    Returns
    --------------------
    Dataframe after full selection.
    If uid was passed, the uid will be recalculated and attached to the dataframe.
    '''

    log.info(60 * '-')
    log.info('Applying cuts')
    log.info(60 * '-')
    for cut_name, cut_value in cuts.items():
        log.debug(f'{cut_name:<40}{cut_value}')
        rdf = rdf.Filter(cut_value, cut_name)

    if out_path:
        _save_cutflow(path=out_path, rdf=rdf, cuts=cuts)

    if uid is None:
        log.debug('No UID found, not updating it')
        return rdf

    log.info('Attaching updated UID and selection to dataframe')
    uid = hashing.hash_object([uid, cuts])
    setattr(rdf, 'uid',  uid) # noqa: B010
    setattr(rdf, 'sel', cuts) # noqa: B010

    return rdf
# ----------------------
