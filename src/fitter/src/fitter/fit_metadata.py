'''
Module holding FitMetadata class
'''
import re

from pathlib   import Path
from typing    import Final
from pydantic  import BaseModel, ConfigDict
from rx_common import Block, Brem, Channel, Component, Project, Qsq
from dmu       import LogStore

from .mva_conf import MVAWp

_COMMON   : Final[str] = r'.*\/(\d+-\d+|\d{3})_(\d+-\d+|\d{3})_(all|b\d)\/(?:reso|rare)\/(rk|rkst)\/(mm|ee)\/(low|central|jpsi|psi2|high)'
_DT_REGEX : Final[str] = r'\/_COMP\/fit\/.*\/brem_([x,0-9]{3})\/parameters.json'
_MC_REGEX : Final[str] = r'\/_COMP\/fit\/brem_([x,0-9]{3})\/brem_[x,0-9]{3}(_b\d)?\/parameters.json'

log=LogStore.add_logger('fitter:fit_metadata')
# -------------------------------
class FitMetadata(BaseModel):
    '''
    Class meant to identify fitted sample 
    '''
    model_config = ConfigDict(frozen=True)

    component : Component
    mva_cmb   : MVAWp
    mva_prc   : MVAWp
    block     : Block
    project   : Project
    channel   : Channel
    q2bin     : Qsq
    brem      : Brem
    # -------------------
    @classmethod
    def from_pars_path(cls, path : Path) -> 'FitMetadata':
        '''
        Parameters
        --------------
        path: Path to parameters.json, i.e. file with fit parameters

        Returns
        --------------
        Object holding fit metadata
        '''
        metadata_path = path.parent / 'metadata.json'
        if metadata_path.exists():
            json_string = metadata_path.read_text()
            return cls.model_validate_json(json_string)

        component = Component.from_path(path = path)

        if component.is_mc:
            regex = f'{_COMMON}{_MC_REGEX}'
        else:
            regex = f'{_COMMON}{_DT_REGEX}'

        regex = regex.replace('_COMP', component)
        mtch  = re.match(regex, str(path))
        if not mtch:
            log.error(f'Regex: {regex}')
            message = f'''
            Path does not conform to pattern

            Path   : {path}
            Pattern: {regex}
            '''
            raise ValueError(message)

        cmb_wp = mtch.group(1)
        prc_wp = mtch.group(2)
        block  = mtch.group(3).removeprefix('b') # b3 -> 3

        return cls(
            component= component,
            mva_cmb  = MVAWp.from_label(cmb_wp),
            mva_prc  = MVAWp.from_label(prc_wp),
            project  = Project(mtch.group(4)),
            channel  = Channel(mtch.group(5)),
            q2bin    = Qsq(    mtch.group(6)),
            block    = Block.from_str(value = block),
            brem     =  Brem.from_str(value = mtch.group(7)))
# -------------------
