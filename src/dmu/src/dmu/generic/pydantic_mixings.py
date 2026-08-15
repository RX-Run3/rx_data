'''
Module holding useful mixings for pydantic models
'''
from gvar                import gvar
from pathlib             import Path
from typing              import Sequence
from dmu                 import LogStore

from .pydantic_protocols import NodeProtocol
from .pydantic_protocols import SupportsModelDumpJson 
from .regular_graph      import RegularGraphMaker, LinkedNode

log=LogStore.add_logger('dmu::generic::pydantic_mixins')
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
        total           = gvar(0, 0)
        valid_neighbors = 0
        log.debug('Patching')
        for lnode in linked_node.neighbours:
            if lnode.gauss is None:
                continue

            log.debug(lnode)
            total           += lnode.gauss
            valid_neighbors += 1

        avg  = total / valid_neighbors 
        node = LinkedNode(
            val         = avg.mean,
            err         = avg.sdev,
            coordinates = linked_node.coordinates)

        log.debug(f'Patched:\n {node}')

        return node
    # ----------------------------------------------
    def _node_location(self, node : NodeProtocol) -> tuple[float,float]:
        loc = node.wp.location
        try:
            x, y = loc
            return x, y
        except Exception as exc:
            raise ValueError(f'Cannot extract location from: {loc}') from exc
    # ----------------------------------------------
    def patch_yields(self, nodes : Sequence[NodeProtocol] ) -> Sequence[LinkedNode]:
        '''
        Parameters
        ----------------
        nodes: List of nodes to be patched

        Returns
        ----------------
        List of nodes that replace missing ones
        '''
        data = { self._node_location(node) : node.gauss for node in nodes }
        rgr  = RegularGraphMaker(data = data)
        grp  = rgr.get_graph()
        res  = [ self._patch(linked_node) for linked_node in grp.missing_nodes ]

        return res
# ---------------------------
