'''
Module holding useful mixings for pydantic models
'''
from gvar                import GVar, gvar
from pathlib             import Path
from typing              import Sequence, TypeVar

from .pydantic_protocols import GridElementProtocol, NodeLocProtocol
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
Node = TypeVar('Node', bound=GridElementProtocol)
Loc  = TypeVar('Loc' , bound=NodeLocProtocol)
class Patchable:
    '''
    Implements:

    patch
    '''
    # ----------------------------------------------
    def _patch(self, linked_node : LinkedNode[Loc]) -> tuple[Loc,GVar]:
        total = gvar(mean = 0, sdev = 0)
        for lnode in linked_node.neighbours:
            var      = gvar(
                mean = lnode.node.val,
                sdev = lnode.node.err)

            total += var

        value = total / len(linked_node.neighbours)
        wp    = linked_node.node.wp

        return wp, value 
    # ----------------------------------------------
    def patch(self, nodes : Sequence[Node] ) -> Sequence[tuple[Loc,GVar]]:
        '''
        Patches missing elements in grid
        '''
        rgr = RegularGraphMaker(nodes = nodes)
        grp = rgr.get_graph()

        return [ self._patch(linked_node) for linked_node in grp.missing_nodes ]
# ---------------------------
