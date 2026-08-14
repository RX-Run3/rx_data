'''
Module holding useful mixings for pydantic models
'''
from pathlib             import Path
from typing              import Generic, TypeVar
from .pydantic_protocols import GridProtocol
from .pydantic_protocols import SupportsModelDumpJson 
from .regular_graph      import RegularGraph

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
T = TypeVar('T', bound=GridProtocol)
class Patchable(Generic[T]):
    '''
    Implements:

    patch
    '''
    # ----------------------------------------------
    def patch(self : T) -> T:
        '''
        Patches missing elements in grid
        '''
        rgr     = RegularGraph(grid = self)
        missing = rgr.get_missing_nodes()

        all_pts = [ *missing , *self.root ]

        return self.model_copy(update = {'root' : all_pts}) 
# ---------------------------
