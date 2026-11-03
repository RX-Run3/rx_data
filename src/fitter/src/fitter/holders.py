'''
Module with Holder class
'''
import copy

from dmu           import LogStore
from rx_common     import Component
from pydantic      import BaseModel, ConfigDict

log = LogStore.add_logger('rx_generic:holder')
# ----------------------
class ComponentHolder[T]:
    '''
    Class meant to be used to store datasets, __getattr__ has been overriden
    to be an accesssor to the underlying elements. Therefore there are no public methods can be
    accessed by name, e.g:

    copy: Call operator
    '''
    _data: dict[Component, T]  # This is purely for type checking
    # ----------------------
    def __init__(self) -> None:
        '''
        '''
        self.__dict__['_data'] = dict()
    # ----------------------
    @property
    def keys(self) -> list[Component]:
        return list(self._data)
    # ----------------------
    def __contains__(self, component : Component) -> bool:
        '''
        Checks if key exists in underlying container
        '''
        return component in self._data
    # ----------------------
    def __setitem__(self, component : Component, value : T) -> None:
        '''
        Allows adding elements to holder
        '''
        if component in self._data:
            raise ValueError(f'Key {component} already found')

        self._data[component] = value
    # ----------------------
    def __iter__(self):
        return iter(self._data)
    # ----------------------
    def items(self):
        return self._data.items()
    # ----------------------
    def __getitem__(self, component : Component) -> T:
        '''
        Allows retrieval of data through square bracket
        '''
        return self._data[component]
    # ----------------------
    def _copy_value(self, value : T) -> T:
        '''
        Parameters
        -------------
        value: Object that has to be copied

        Returns
        -------------
        Copy of object
        '''
        try:
            new_value = copy.deepcopy(value)
        except Exception as exc:
            obj_type = type(value)
            raise ValueError(f'Cannot copy objects of type: {obj_type}') from exc

        return new_value
    # ----------------------
    def __call__(
        self,
        update : dict[Component,T] | None = None) -> 'ComponentHolder[T]':
        '''
        Parameters
        -------------
        update: Dictionary with elements that need to be replaced in the copied holder

        Returns
        -------------
        Copy of current holder with elements also copied, all copies are deep copies.
        '''
        if update is None:
            update = dict()

        new_holder = ComponentHolder[T]()

        for key, value in self._data.items():
            if key in ['__orig_class__']:
                continue

            log.debug(f'Copying: {key}')
            if key not in update:
                copy_value      = self._copy_value(value = value)
                new_holder[key] = copy_value
            else:
                val             = update[key]
                new_holder[key] = val

        return new_holder
# ----------------------
class ChannelHolder[T](BaseModel, frozen = True):
    '''
    Class mean to hold objects per channel
    '''
    model_config = ConfigDict(arbitrary_types_allowed=True)

    ee : T
    mm : T
# ----------------------
