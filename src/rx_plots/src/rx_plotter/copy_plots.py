'''
Module holding CopyPlots class
'''
from pathlib     import Path
from pydantic    import BaseModel, Field
from dmu.generic import utilities as gut
from dmu         import LogStore

log=LogStore.add_logger('rx_plots:copy_plots')
# -------------------------------------------------
class Section(BaseModel):
    '''
    Class representing files to be copied from given source to given target paths
    all sharing the same file tree
    '''
    extensions : list[str] = Field(description = 'List of image extensions, e.g. png, pdf, etc')
    source_dir : str       = Field(description = 'Environment variable with root of source directory')
    target_dir : str       = Field(description = 'Environment variable with root of target directory')
    source     : str       = Field(description = 'Environment variable with source directory WRT root')
    target     : str       = Field(description = 'Environment variable with target directory WRT root')
    # -------------------------------------------------
    @property
    def paths(self) -> dict[Path, Path]:
        '''
        Dictionary mapping existing path to desired location
        '''
        return {} 
# -------------------------------------------------
class CopyPlotsConf(BaseModel):
    '''
    Class configuring how plots will be copied
    '''
    extensions : list[str]     = Field(description = 'List of image extensions, e.g. png, pdf, etc')
    source_dir : str           = Field(description = 'Environment variable with source directory')
    target_dir : str           = Field(description = 'Environment variable with target directory')
    paths      : dict[str,str] = Field(description = 'Mappings between source and target tree structures')
    # -------------------------------------------------
    @classmethod
    def from_name(cls, name : str) -> 'CopyPlotsConf':
        '''
        Parameters
        ----------------
        name: Name of file with configuration, e.g. fit_plots

        Return
        ----------------
        Instance of configuration
        '''
        data = gut.load_data(package = 'rx_plotter_data', fpath = f'copy/{name}.yaml')

        return cls(**data)
    # -------------------------------------------------
    @property
    def sections(self) -> list[Section]:
        '''
        List of objects describing how to copy a set of
        plots living in a given directory sturcture
        '''
        objs : list[Section] = []
        for source, target in self.paths.items():
            obj = Section(
                source     = source,
                target     = target,
                source_dir = self.source_dir,
                target_dir = self.target_dir,
                extensions = self.extensions)

            objs.append(obj)

        return objs
# -------------------------------------------------
class CopyPlots:
    '''
    Class meant to copy plots from a given set of directory paths to another
    '''
    # -------------------------------------------------
    def __init__(self, cfg : CopyPlotsConf):
        '''
        Parameters
        ----------------
        cfg: Config object
        '''
        self._cfg = cfg
    # -------------------------------------------------
    def run(self, dry_run : bool) -> None:
        '''
        Runs copy

        Parameters
        -----------------
        dry_run: If True will do everything but the actual copy of the files
        '''
        if dry_run:
            log.warning('Running dry-run')

        for section in self._cfg.sections:
            for source, target in section.paths.items():
                if dry_run:
                    log.info(source)
                    log.info('--->')
                    log.info(target)
                    log.info('')
                    continue

                target.hardlink_to(source)
    # -------------------------------------------------
    @classmethod
    def from_config_name(cls, name : str) -> 'CopyPlots':
        '''
        Parameters
        ----------------
        name: Name of config file

        Returns
        ----------------
        Instance of copy tool
        '''
        cfg = CopyPlotsConf.from_name(name = name)

        return cls(cfg = cfg)
# -------------------------------------------------
