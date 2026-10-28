'''
Script used to validate ntuples produced by AP pipelines
'''
import yaml
import uproot
import argparse

from functools import cached_property
from pathlib   import Path
from ROOT      import RDF, RDataFrame
from typing    import Final, Generic, TypeVar
from pydantic  import BaseModel, model_validator, ConfigDict

T = TypeVar('T')
_TREENAME : Final[str] = 'DecayTree'
# -------------------------------
class Config(BaseModel):
    '''
    Class meant to configure validation
    '''
    model_config = ConfigDict(frozen = True)

    old : Path
    new : Path
    exp : list[str]
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
class IndentedDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        _ = indentless

        return super().increase_indent(flow=flow, indentless=False)
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
    @cached_property
    def summary(self) -> dict[str,bool] | None:
        '''
        None if both new and old exist
        Dictionary signaling if an object exists or not
        '''
        if self.old and self.new:
            return None

        return {  
            'old' : self.old is not None,
            'new' : self.new is not None,
        }
# -------------------------------
class RDFHolder(Holder):
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
    def tree_summary(self, cfg : Config) -> dict[str,list[str] | None]:
        '''
        Dictonary mapping tree label to:

        - List of branches that only exist in this tree
        - None if the tree itself does not exist
        '''
        summary : dict[str,list[str] | None] = {}

        only_in_old : list[str] = [ col for col in self.old_cols if col not in self.new_cols and not any(subs in col for subs in cfg.exp) ]
        only_in_new : list[str] = [ col for col in self.new_cols if col not in self.old_cols and not any(subs in col for subs in cfg.exp) ]

        summary['old'] = None if self.old is None else only_in_old
        summary['new'] = None if self.new is None else only_in_new

        return summary
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
    with uproot.open(path = path) as ifile: # type: ignore
        dirs = ifile.keys(filter_classname = 'TDirectory') 
        dirs = [ dirname.split(';')[0] for dirname in dirs ]

    return dirs
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
    parser.add_argument('-o', '--old', type =str, help='Path to old/reference file'   , required = True)
    parser.add_argument('-n', '--new', type =str, help='Path to new file, to validate', required = True)
    parser.add_argument('-e', '--exp', nargs='+', help='Substrings that will be used to ignore missing branches')
    args   = parser.parse_args()

    return Config(
        exp = [] if not args.exp else args.exp,
        old = args.old,
        new = args.new)
# -------------------------------
def main():
    cfg   = _get_conf()
    dirs  = _get_directories(cfg = cfg)
    trees = _get_trees(cfg = cfg, dirs = dirs)

    dirs_summaries = { dir.name  : dir.summary for dir  in dirs  if dir.summary is not None }
    tree_summaries = { tree.name : tree.tree_summary(cfg = cfg) for tree in trees }

    data = {
        'Directories' : dirs_summaries,
        'Trees'       : tree_summaries
    }

    with open('summary.yaml', 'w') as ofile:
        string = yaml.dump(
            data               = data, 
            default_flow_style = False, 
            Dumper             = IndentedDumper)
        ofile.write(string)
# -------------------------------
if __name__ == '__main__':
    main()
