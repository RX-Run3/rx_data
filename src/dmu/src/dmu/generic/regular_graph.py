'''
Module holding the RegularGraph class
'''

from typing              import Sequence
from .pydantic_protocols import GridProtocol
from .pydantic_protocols import GridElementProtocol

# ---------------------------------
class RegularGraph:
    '''
    Class meant to represent an regular graph in 2D i.e.
    a graph where the edges live at the same distance from each other
    '''
    def __init__(self, grid : GridProtocol):
        '''
        Parameters
        --------------
        grid: Object holding nodes at different locations
        '''
        self.__grid = grid
    # ---------------------------------
    def get_missing_nodes(self) -> Sequence[GridElementProtocol]:
        '''
        Returns
        ------------------
        Container with grid elements, for missing elements
        These elements were interpolated
        '''
        return []
# ---------------------------------
