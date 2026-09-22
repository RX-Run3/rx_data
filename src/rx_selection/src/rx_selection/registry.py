'''
Module with Registry class
'''
from typing     import ClassVar
from rx_common  import Component, Trigger, Qsq, Cuts
from .selection import selection

type Sel = dict[Cuts, str]
type Key = tuple[Component, Trigger, Qsq]
# -----------------------------
class Registry:
    '''
    Class meant to store selection information
    for a given analysis
    '''
    _registry : ClassVar[dict[Key,Sel]] = {}
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
        if self._key in self._registry:
            raise ValueError(f'Selection already set for: {self._key}')

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
        default    = selection(q2bin = qsq, process = component, trigger = trigger)

        result : Sel = dict()
        for key, val in registered.items():
            if key in default and default[key] == val:
                continue

            result[key] = val

        return result
# -----------------------------
