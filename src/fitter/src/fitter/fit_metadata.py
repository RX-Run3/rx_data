'''
Module holding FitMetadata class
'''
import re

from pathlib    import Path
from pydantic   import BaseModel
from dmu        import LogStore
from rx_common  import Block, Brem, Channel, Component, Project, Qsq
from .mva_conf  import MVAWp

_COMMON   = r'.*\/(\d{3}-\d{3}|\d{3})_(\d{3}-\d{3}|\d{3})_(all|b\d)\/(?:reso|rare)\/(rk|rkst)\/(mm|ee)\/(low|central|jpsi|psi2|high)'
_DT_REGEX = r'\/data_24\/fit\/.*\/brem_([x,0-9]{3})\/parameters.json'
_MC_REGEX = r'\/_SIGNAL\/fit\/brem_([x,0-9]{3})\/brem_[x,0-9]{3}\/parameters.json'

log=LogStore.add_logger('fitter:fit_metadata')
# -------------------------------
class FitMetadata(BaseModel):
    '''
    Class meant to store fit information
    '''
    mva_cmb : MVAWp
    mva_prc : MVAWp
    block   : Block
    project : Project
    channel : Channel
    q2bin   : Qsq
    brem    : Brem
    # -------------------
    @classmethod
    def from_path(
        cls, 
        path : Path,
        comp : Component) -> 'FitMetadata':
        '''
        Parameters
        --------------
        path: Path to parameters.json, i.e. file with fit parameters
        comp: Component, e.g. signal or data

        Returns
        --------------
        Object holding fit metadata
        '''
        if comp.is_mc:
            REGEX = f'{_COMMON}{_MC_REGEX}'
            REGEX = REGEX.replace('_SIGNAL', comp)
        else:
            REGEX = f'{_COMMON}{_DT_REGEX}'

        mtch = re.match(REGEX, str(path))
        if not mtch:
            log.error(f'Regex: {REGEX}')
            raise ValueError(f'Path does not conform to pattern: {path}')

        cmb_wp = mtch.group(1)
        prc_wp = mtch.group(2)

        return cls(
            mva_cmb = MVAWp.from_label(cmb_wp),
            mva_prc = MVAWp.from_label(prc_wp),
            project = Project(mtch.group(4)),
            channel = Channel(mtch.group(5)),
            q2bin   = Qsq(    mtch.group(6)),
            block   = Block.from_str(value = mtch.group(3)),
            brem    =  Brem.from_str(value = mtch.group(7)),
        )
    # -------------------
    @classmethod
    def from_pars_path(
        cls, 
        path : Path,
        comp : Component) -> 'FitMetadata':
        '''
        Parameters
        --------------
        path: Path to parameters.json, i.e. file with fit parameters
        comp: Component, e.g. signal or data

        Returns
        --------------
        Object holding fit metadata
        '''
        metadata_path = path.parent / 'metadata.json'
        if metadata_path.exists():
            json_string = metadata_path.read_text()
            return cls.model_validate_json(json_string)

        return cls.from_path(path = path, comp = comp)
# -------------------
