'''
Module holding the RegularGraph class
'''
from gvar     import GVar, gvar
from typing   import Self, Sequence
from pydantic import BaseModel

# ---------------------------------
class LinkedNode(BaseModel):
    '''
    Class representing node with links
    to neighbouring nodes
    '''
    coordinates : tuple[float,...]
    val         : float
    err         : float
    # ------------------------------
    @property
    def gauss(self) -> GVar:
        '''
        Random Gaussian variable with node's data
        '''
        return gvar(mean = self.val, sdev = self.err)
    # ------------------------------
    @property
    def neighbours(self) -> Sequence[Self]:
        '''
        List of linked nodes neighbouring current one
        '''
        return []
# ---------------------------------
class RegularGraph:
    '''
    Class meant to represent an regular graph in 2D i.e.
    a graph where the edges live at the same distance from each other
    '''
    # ------------------------------
    @property
    def missing_nodes(self) -> Sequence[LinkedNode]:
        '''
        List of nodes where data is missing
        '''
        return []
# ---------------------------------
class RegularGraphMaker:
    '''
    Maker of RegularGraph objects
    '''
    # ---------------------------------
    def __init__(self, nodes : dict[tuple[float,...],GVar]):
        '''
        Parameters
        --------------
        grid: Object holding nodes at different locations
        '''
        self.__nodes = nodes 
    # ---------------------------------
    def get_graph(self) -> RegularGraph:
        '''
        Returns
        ------------------
        Container with grid elements, for missing elements
        These elements were interpolated
        '''
        return 
# ---------------------------------
