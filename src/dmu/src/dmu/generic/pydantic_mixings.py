'''
Module holding useful mixings for pydantic models
'''
from pathlib import Path
from typing  import Protocol

# ---------------------------
class _SupportsModelDumpJson(Protocol):
    def model_dump_json(self, indent: int) -> str: ...
# ---------------------------
class Serializable:
    '''
    Implements:

    to_json
    '''
    # ---------------------------
    def to_json(self : _SupportsModelDumpJson, path : Path) -> None:
        '''
        Parameters
        ---------------
        path: Path to JSON file where current object will be serialized
        '''
        path.parent.mkdir(parents = True, exist_ok = True)

        string = self.model_dump_json(indent = 2)
        path.write_text(string)
# ---------------------------
