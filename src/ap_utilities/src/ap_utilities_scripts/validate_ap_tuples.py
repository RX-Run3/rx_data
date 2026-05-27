'''
Script used to validate ntuples produced by AP pipelines
'''

import yaml
import argparse

from functools import cached_property
from pathlib   import Path
from ROOT      import TFile, TDirectory, RDF, RDataFrame # type: ignore
from typing    import Final, Generic, TypeVar
from pydantic  import BaseModel, model_validator, ConfigDict

T = TypeVar('T')
_TREENAME : Final[str] = 'DecayTree'
# -------------------------------
class Holder(BaseModel, Generic[T]):
    '''
    Class meant to hold an old version and a new version
    of a generic object
    '''
    model_config = ConfigDict(frozen = True)

    name: str
    old : T | None
    new : T | None
    # -------------------------------
    @model_validator(mode = 'after')
    def _validate(self) -> 'Holder':
        if self.old is None and self.new is None:
            raise ValueError('Neither old nor new version found')

        return self
    # -------------------------------
    @property
    def summary(self) -> dict[str,bool]:
        '''
        Dictionary signaling if an object exists or not
        '''
        return { 
            f'old_{self.name}' : self.old is not None,
            f'new_{self.name}' : self.new is not None,
        }
# -------------------------------
class RDFHolder(Holder[RDF.RNode]):
    '''
    Class meant to hold dataframes
    '''
    model_config = ConfigDict(arbitrary_types_allowed = True)
    # ---------
    def _get_cols(self, rdf : RDF.RNode | None) -> list[str]:
        if rdf is None:
            return [] 

        return [ col.c_str() for col in rdf.GetColumnNames() ]
    # ---------
    @cached_property
    def old_cols(self) -> list[str]:
        return self._get_cols(rdf = self.old)
    # ---------
    @cached_property
    def new_cols(self) -> list[str]:
        return self._get_cols(rdf = self.new)
    # ---------
    @property
    def tree_summary(self) -> dict[str,list[str] | None]:
        '''
        Dictonary mapping tree label to:

        - List of branches that only exist in this tree
        - None if the tree itself does not exist
        '''
        summary : dict[str,list[str] | None] = {}

        only_in_new : list[str] = [ col for col in self.new_cols if col not in self.old_cols ]
        only_in_old : list[str] = [ col for col in self.old_cols if col not in self.new_cols ]

        summary[f'old_{self.name}'] = None if self.old is None else only_in_old
        summary[f'new_{self.name}'] = None if self.new is None else only_in_new

        return summary
# -------------------------------
class Config(BaseModel):
    '''
    Class meant to configure validation
    '''
    model_config = ConfigDict(frozen = True)

    old : Path
    new : Path
    # -------------------------------
    def get_rdf(self, dirname : str | None, is_old : bool) -> RDF.RNode | None:
        '''
        Parameters
        ------------------
        dirname: Name of directory holding DecayTree, None, if missing
        is_old : If True, use old file

        Returns
        ------------------
        Dataframe associated or None if no dataframe found
        '''
        if dirname is None:
            return None

        path = self.old if is_old else self.new

        if not path.exists():
            return None

        return RDataFrame(f'{dirname}/{_TREENAME}', str(path))
# -------------------------------
def _get_directory_names(path : Path) -> list[str]:
    '''
    Parameters
    ----------------
    path: Path to ROOT file

    Returns
    ----------------
    List of directory names in file
    '''
    with TFile(str(path), 'read') as ifile:
        keys = ifile.GetKeys()
        objs = [ key.ReadObj() for key in keys ]
        dirs = [ obj for obj in objs if isinstance(obj, TDirectory) ]

        return [ _dir.GetName() for _dir in dirs ]
# -------------------------------
def _get_directories(cfg : Config) -> list[Holder[str]]:
    '''
    Returns
    ---------------
    List of holders of directories
    '''
    old_names = _get_directory_names(path = cfg.old)
    new_names = _get_directory_names(path = cfg.new)

    all_names = old_names + new_names
    holders : list[Holder[str]] = []
    for name in sorted(list(set(all_names))):
        hdr      = Holder[str](
            name = name,
            old  = name if name in old_names else None,
            new  = name if name in new_names else None)

        holders.append(hdr)

    return holders
# -------------------------------
def _get_trees(
    cfg  : Config, 
    dirs : list[Holder[str]]) -> list[RDFHolder]:
    '''
    Parameters
    ---------------
    cfg : Configuration
    dirs: Holder of directory names 

    Returns
    ---------------
    List of holders of dataframes
    '''
    holders : list[RDFHolder] = []
    for dir_holder in dirs:
        rdf_holder = RDFHolder(
            name= dir_holder.name,
            old = cfg.get_rdf(dirname = dir_holder.old, is_old =  True),
            new = cfg.get_rdf(dirname = dir_holder.new, is_old = False),
        )

        holders.append(rdf_holder)

    return holders
# -------------------------------
def _get_conf() -> Config:
    '''
    Returns
    ----------
    config object built from arguments
    '''
    parser = argparse.ArgumentParser(description='Script used to plot histograms in pkl files created by PIDCalib2')
    parser.add_argument('-o', '--old', type=str, help='Path to old/reference file'   , required = True)
    parser.add_argument('-n', '--new', type=str, help='Path to new file, to validate', required = True)
    args   = parser.parse_args()

    return Config(
        old = args.old,
        new = args.new)
# -------------------------------
def main():
    cfg   = _get_conf()
    dirs  = _get_directories(cfg = cfg)
    trees = _get_trees(cfg = cfg, dirs = dirs)

    dirs_summaries = [ dir.summary       for dir  in dirs  ]
    tree_summaries = [ tree.tree_summary for tree in trees ]

    data = {
        'Directories' : dirs_summaries,
        'Trees'       : tree_summaries
    }

    with open('summary.yaml', 'w') as ofile:
        string = yaml.safe_dump(data, indent = 2)
        ofile.write(string)
# -------------------------------
if __name__ == '__main__':
    main()
