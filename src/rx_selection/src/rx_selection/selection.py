'''
Module containing the selection function, which returns a dictionary of cuts
'''

import copy
import yaml

from functools              import cache
from pathlib                import Path
from contextlib             import contextmanager
from contextvars            import ContextVar
from importlib.resources    import files
from ROOT                   import RDF
from dmu                    import LogStore
from dmu.generic            import hashing
from dmu.rdataframe         import utilities          as rut
from dmu.generic            import utilities          as gut
from rx_selection           import truth_matching     as tm
from rx_common              import Component
from rx_common              import Qsq, QsqDef, Trigger, Cuts

log=LogStore.add_logger('rx_selection:selection')

_OVERRIDING_QSQ : ContextVar[None|QsqDef] = ContextVar('_OVERRIDING_QSQ', default = None)
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
def override_qsq(kind : QsqDef):
    '''
    Parameters
    ---------------
    Kind: q2 type that should be used inside this context
    for selection
    '''
    old_value = _OVERRIDING_QSQ.get()
    _OVERRIDING_QSQ.set(kind)
    try:
        yield
    finally:
        _OVERRIDING_QSQ.set(old_value)
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
    skip_truth: bool = False) -> dict[Cuts,str]:
    '''
    Picks up sample name, trigger, etc, returns dictionary with selection

    q2bin     : low, central, jpsi, psi2S or high
    process   : Nickname for MC sample, starts with "DATA" for data
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
        trig   = trigger,
        q2_bin = q2bin)
    d_cut.update(d_tmp)

    if Data.d_custom_selection is not None:
        try:
            d_cut.update(Data.d_custom_selection)
        except ValueError as exc:
            log.error(yaml.dump(Data.d_custom_selection))
            raise ValueError('Cannot update selection') from exc

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
def _preprocess_cut(cut : Cuts, cut_val : str) -> str:
    if cut == Cuts.q2:
        cut_val = _preprocess_qsq_cut(cut_val)

    return cut_val
#-----------------------
def _preprocess_qsq_cut(expr : str) -> str:
    '''
    Parameters
    --------------
    expr: String with the cut expression, e.g. q2 > 100000

    Returns
    --------------
    Updated cut expression
    '''
    qsq_kind = _OVERRIDING_QSQ.get()
    if qsq_kind is None:
        return expr

    log.info(f'Default: {expr}')
    expr = qsq_kind.update_expression(expr = expr)
    log.info(f'New    : {expr}')

    return expr
#-----------------------
# TODO: Add types
def _get_selection(
    trig   : Trigger,
    q2_bin : Qsq) -> dict[Cuts,str]:
    '''
    Parameters
    -----------------
    trig  : Hlt2 trigger
    q2_bin: q2 bin e.g. central, needed to pick for q2 dependent cuts

    Returns
    -----------------
    Dictionary with:

    key  : Label of cut, e.g. q2
    value: Cut expression e.g. q2 > 1e6
    '''
    cfg = _load_selection_config()

    if trig.project not in cfg:
        for key in cfg:
            log.error(key)
        raise ValueError(f'Cannot find {trig.project} in config')

    if trig.channel not in cfg[trig.project]:
        raise ValueError(f'Cannot find {trig.channel} in config section for {trig.project}')

    d_cut = cfg[trig.project][trig.channel]
    if isinstance(d_cut, str):
        raise ValueError(f'Selection for {trig} is a string: {d_cut}')

    d_new : dict[Cuts,str] = {}
    for cut_name, d_q2bin in d_cut.items():
        cut = Cuts(cut_name)

        if isinstance(d_q2bin, str):
            d_new[cut] = _preprocess_cut(cut=cut, cut_val=d_q2bin)
            continue

        if q2_bin not in d_q2bin:
            for val in d_q2bin:
                log.error(val)

            raise ValueError(f'Cannot find q2 bin {q2_bin} in {cut_name} section')

        cut_val = d_q2bin[q2_bin]
        log.debug(f'Overriding {cut_name} for {q2_bin}')

        d_new[cut] = _preprocess_cut(cut=cut, cut_val=cut_val)

    return d_new
#-----------------------
def save_cutflow(
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

    setattr(rdf, 'sel', d_sel) # noqa: B010

    if isinstance(out_path, Path):
        save_cutflow(path=out_path, rdf=rdf, cuts=d_sel)
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
        rdf = rdf.Filter(cut_value, str(cut_name))

    if out_path:
        save_cutflow(path=out_path, rdf=rdf, cuts=cuts)

    if uid is None:
        log.debug('No UID found, not updating it')
        return rdf

    log.info('Attaching updated UID and selection to dataframe')
    uid = hashing.hash_object([uid, cuts])
    setattr(rdf, 'uid',  uid) # noqa: B010
    setattr(rdf, 'sel', cuts) # noqa: B010

    return rdf
# ----------------------
