'''
Module holding Specification and Sample classes
'''
from pathlib   import Path
from ROOT      import RDataFrame # type: ignore
from pydantic  import BaseModel, ConfigDict

# --------------------------
class Sample(BaseModel):
    '''
    Class meant to represent a sample
    '''
    files    : list[Path]
    trees    : list[str]
    metadata : dict[str,str]
    # --------------------
    @property
    def size(self) -> int:
        '''
        Number of entries in this sample
        '''
        if len(self.trees) != 1:
            raise ValueError(f'Not one and only one tree name found: {self.trees}')

        tree_name = self.trees[0]

        paths = [ str(path) for path in self.files ]
        rdf   = RDataFrame(tree_name, paths)

        return rdf.Count().GetValue()
# --------------------------
class Specification(BaseModel):
    '''
    Class meant to represent a specification needed
    to build ROOT dataframes
    '''
    friends : dict[str,Sample]
    samples : dict[str,Sample]

    model_config = ConfigDict(frozen=True)
