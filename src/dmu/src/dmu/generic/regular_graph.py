'''
Module holding the RegularGraph class
'''
from gvar     import GVar, gvar
from typing   import Any, Sequence
from pydantic import BaseModel, RootModel
from dmu      import LogStore

log=LogStore.add_logger('dmu:generic:regular_graph')
# ---------------------------------
class LinkedNode(BaseModel, frozen = True):
    '''
    Class representing node with links
    to neighbouring nodes
    '''
    coordinates : tuple[float,float]
    val         : float | None
    err         : float | None
    neighbours  : list['LinkedNode'] = []
    # ------------------------------
    def __str__(self):
        nei_coo     = [ str(nei.coordinates) for nei in self.neighbours ]
        nei_coo_str = ';'.join(nei_coo)

        msg = f'''
        val: {self.val}
        err: {self.err}
        loc: {self.coordinates}
        nei: {nei_coo_str}
        '''

        return msg
    # ------------------------------
    @property
    def is_valid(self) -> bool:
        '''
        True if value of Node is not None
        '''
        if any(x is None for x in [self.val, self.err]):
            return False

        return True
    # ------------------------------
    def link(self, other : 'LinkedNode') -> None:
        '''
        Stores other node in neighbours
        '''
        if other == self:
            raise ValueError('Cannot link node to itself')

        if other in self.neighbours:
            return

        self.neighbours.append(other)

        other.link(self)
    # ------------------------------
    def __hash__(self) -> int:
        return hash(self.coordinates) + hash(self.val) + hash(self.err)
    # ------------------------------
    def __eq__(self, other) -> bool:
        if not isinstance(other, LinkedNode):
            raise NotImplementedError('Only comparison between LinkedNodes implemented')

        if self.coordinates != other.coordinates:
            return False

        if self.val != other.val or self.err != other.err:
            raise ValueError('Found nodes at the same coordinates with different values')

        return True
    # ------------------------------
    @property
    def gauss(self) -> GVar | None:
        '''
        Random Gaussian variable with node's data
        '''
        if self.val is None or self.err is None:
            return None

        return gvar(self.val, self.err)
# ---------------------------------
class RegularGraph(RootModel[list[LinkedNode]], frozen = True):
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
        return [ node for node in self.root if not node.is_valid ]
# ---------------------------------
class _NodeData(RootModel[list[tuple[float,float,Any]]], frozen = True):
    '''
    Holder of data used to make linked nodes
    '''
    # --------------------------
    def at(self, permutate : bool) -> '_NodeData':
        def _sorter(arg : tuple[float,float,GVar | None]):
            x, y, _ = arg
            if not permutate:
                return x, y

            return y, x

        data = sorted(self.root, key = _sorter)

        return _NodeData(root = data)
# ---------------------------------
class RegularGraphMaker:
    '''
    Maker of RegularGraph objects
    '''
    # ---------------------------------
    def __init__(self, data : dict[tuple[float,float], GVar]):
        '''
        Parameters
        --------------
        data: dictionary mapping coordinates of node with value as a random variable
        '''
        self.__data = data
    # ---------------------------------
    def __get_data(self) -> _NodeData:
        '''
        Returns all nodes possible with the x and y coordinates in __data
        values are None when a node is not found at a given (x,y)
        '''
        locs  = [ loc      for loc     in self.__data ]
        xs    = { xval     for xval, _ in locs }
        ys    = { yval     for _, yval in locs }
        pairs = [ (xv, yv) for xv in xs for yv in ys ]

        res : list[tuple[float,float, GVar | None]] = []
        for pair in pairs:
            x, y = pair
            z    = None if pair not in self.__data else self.__data[pair]
            elm  = x, y , z

            if z is None:
                log.debug(f'{x:<20}{y:<20}{"None":<20}')
            else:
                val = f'({z.mean}, {z.sdev})'
                log.debug(f'{x:<20}{y:<20}{val:<20}')

            res.append(elm)

        return _NodeData(root = res)
    # ---------------------------------
    def __add_nodes(self, data : _NodeData, nodes : dict[tuple[float,float],LinkedNode]) -> dict[tuple[float,float],LinkedNode]:
        '''
        Parameters
        ----------------
        data : Object holding data used to create nodes
        nodes: dictionary mapping location of nodes with nodes

        Return
        ----------------
        List of linked nodes
        '''
        last_node : LinkedNode | None = None
        last_x    : float      | None = None
        last_y    : float      | None = None
        for x, y, rvar in data.root:
            loc = x, y
            val = None if rvar is None else rvar.mean
            err = None if rvar is None else rvar.sdev

            if loc in nodes:
                node = nodes[loc]
            else:
                node = LinkedNode(
                    val         = val,
                    err         = err,
                    coordinates = loc)

            if last_x is None or last_y is None:
                nodes[loc] = node
                last_x, last_y, last_node = x, y, node
                continue

            if x < last_x or y < last_y:
                last_node = None

            if last_node:
                node.link(last_node)

            last_x, last_y, last_node = x, y, node
            if loc not in nodes:
                nodes[loc] = node

        return nodes
    # ---------------------------------
    def get_graph(self) -> RegularGraph:
        '''
        Returns
        ------------------
        Container with grid elements, for missing elements
        These elements were interpolated
        '''
        nodes : dict[tuple[float,float],LinkedNode] = dict()
        data  = self.__get_data()

        data  = data.at(permutate = False)
        nodes = self.__add_nodes(data = data, nodes = nodes)

        data  = data.at(permutate =  True)
        nodes = self.__add_nodes(data = data, nodes = nodes)

        return RegularGraph(root = list(nodes.values()))
# ---------------------------------
