'''
Module holding useful mixings for pydantic models
'''
from gvar                import gvar
from pathlib             import Path
from typing              import Sequence

from .pydantic_protocols import NodeProtocol
from .pydantic_protocols import SupportsModelDumpJson 
from .regular_graph      import RegularGraphMaker, LinkedNode

# ---------------------------
class Serializable:
    '''
    Implements:

    to_json
    '''
    # ---------------------------
    def to_json(self : SupportsModelDumpJson, path : Path) -> None:
        '''
        Parameters
        ---------------
        path: Path to JSON file where current object will be serialized
        '''
        path.parent.mkdir(parents = True, exist_ok = True)

        string = self.model_dump_json(indent = 2)
        path.write_text(string)
# ---------------------------
class Patchable:
    '''
    Implements:

    patch
    '''
    # ----------------------------------------------
    def _patch(self, linked_node : LinkedNode) -> LinkedNode:
        total = gvar(mean = 0, sdev = 0)
        for lnode in linked_node.neighbours:
            total += lnode.gauss

        avg = total / len(linked_node.neighbours)

        return LinkedNode(
            val         = avg.mean,
            err         = avg.sdev,
            coordinates = linked_node.coordinates)
    # ----------------------------------------------
    def patch(self, nodes : Sequence[NodeProtocol] ) -> Sequence[LinkedNode]:
        '''
        Patches missing elements in grid
        '''
        data = { node.wp.location : node.gauss for node in nodes }
        rgr  = RegularGraphMaker(nodes = data)
        grp  = rgr.get_graph()
        res  = [ self._patch(linked_node) for linked_node in grp.missing_nodes ]

        return res
# ---------------------------
