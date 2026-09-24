'''
Module with Registry class
'''
from typing     import Final
from dmu        import LogStore
from typing     import ClassVar
from rx_common  import Component, Trigger, Qsq, Cuts
from .          import selection as sel

type Sel = dict[Cuts, str]
type Key = tuple[Component, Trigger, Qsq]

log=LogStore.add_logger('rx_selection:registry')

# These are values for cuts that are not really applied, e.g. block == (1)
# Skip them in the building of the difference of selections
_SKIPPED_VALUES : Final[list[str]] = ['(1)', 'true']

# TODO: Improve this eventually
# nbrem was excluded in special way, do not use it as part of binning
_SKIPPED_KEYS   : Final[list[str]] = ['nbrem']
# -----------------------------
class Registry:
    '''
    Class meant to store selection information
    for a given analysis
    '''
    _registry : ClassVar[dict[Key,Sel]] = {}
    _can_override : ClassVar[bool]      = True
    # --------------------------------------
    def __init__(
        self,
        *,
        component : Component,
        trigger   : Trigger,
        qsq       : Qsq):
        '''
        Parameters
        ---------------
        component: Describe sample
        trigger  : E.g. rk
        qsq      : E.g. high
        '''
        self._key = component, trigger, qsq
    # --------------------------------------
    def set(self, cuts : Sel) -> None:
        '''
        Registers selection

        Parameters
        ---------------
        cuts: Dictionary mapping cut enum to expression
        '''
        if self._key in self._registry and not self._can_override:
            raise ValueError(f'Selection already set for: {self._key}')

        if self._key in self._registry:
            log.info(f'Overriding: {self._key}')

        self._registry[self._key] = cuts
    # --------------------------------------
    def get(self) -> Sel:
        '''
        Returns selection associated to object
        '''
        if self._key not in self._registry:
            raise ValueError(f'Selection not found for: {self._key}')

        return self._registry[self._key]
    # --------------------------------------
    @property
    def diff(self) -> Sel:
        '''
        Selection made from any cut living in the registered
        selection that does not exist in the default one
        or that exists with a different value
        '''
        component, trigger, qsq = self._key

        registered = self.get()
        # Pick default selection
        with sel.custom_selection(d_sel = dict(), force_override= True):
            default = sel.selection(q2bin = qsq, process = component, trigger = trigger)

        result : Sel = dict()
        for key, val in registered.items():
            if key in default and default[key] == val:
                continue

            if val in _SKIPPED_VALUES:
                continue

            if key in _SKIPPED_KEYS:
                continue

            result[key] = val

        return result
# -----------------------------
