'''
Module holding FitSummary class
'''
import os
import re
import math
import pandas as pnd

from gvar          import gvar
from functools     import cached_property
from dmu           import LogStore
from dmu.stats     import FitResult
from dmu.generic   import utilities as gut
from pathlib       import Path
from typing        import Final, Sequence
from pydantic      import RootModel
from pydantic      import BaseModel
from rx_common     import Block, Brem, Channel, Component, Project, Qsq

from .mva_conf     import MVAWp

log=LogStore.add_logger('fitter:fit_summary')

_ANADIR   : Final[Path]      = Path(os.environ['ANADIR'])
_COMMON   : Final[str]       = r'.*\/(\d+-\d+|\d{3})_(\d+-\d+|\d{3})_(all|b\d)\/(?:reso|rare)\/(rk|rkst)\/(mm|ee)\/(low|central|jpsi|psi2|high)'
_DT_REGEX : Final[str]       = r'\/data_24\/fit\/.*\/brem_([x,0-9]{3})\/parameters.json'
_MC_REGEX : Final[str]       = r'\/_SIGNAL\/fit\/brem_([x,0-9]{3})\/brem_[x,0-9]{3}(_b\d)?\/parameters.json'
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
        comp: Component representing dataset been fitted

        Returns
        --------------
        Object holding fit metadata
        '''
        if comp.is_mc:
            regex = f'{_COMMON}{_MC_REGEX}'
            regex = regex.replace('_SIGNAL', comp)
        else:
            regex = f'{_COMMON}{_DT_REGEX}'

        mtch = re.match(regex, str(path))
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
            mva_cmb = MVAWp.from_label(cmb_wp),
            mva_prc = MVAWp.from_label(prc_wp),
            project = Project(mtch.group(4)),
            channel = Channel(mtch.group(5)),
            q2bin   = Qsq(    mtch.group(6)),
            block   = Block.from_str(value = block),
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
# -------------------------------
class FitOutputConf(RootModel):
    '''
    Class representing configuration for reading parameters
    '''
    root : dict[Qsq,dict[Project,dict[Channel, Component]]]
# -------------------------------
class FitOutput:
    '''
    Class meant to symbolize a given fit
    '''
    # -------------------------------
    def __init__(self, path : Path, cfg : FitOutputConf):
        '''
        Parameters
        --------------
        path: Path to JSON file with fit parameters 
        cfg : Configuration object 
        '''
        self.__path = path
        self.__cfg  = cfg
        self.__meta = FitMetadata.from_path(path = path, comp = self.dataset)
    # -------------------------------
    def __str__(self):
        msg  ='\n-------------------------\n'
        msg +=f'{"Name":<50}{"Value"}\n'
        msg += '-------------------------\n'
        for key, val in self.info.items():
            msg += f'{key:<50}{val}\n'

        return msg
    # -------------------------------
    @property
    def info(self) -> dict[str, float | str]:
        '''
        Dictionary mapping name of column with value,
        corresponds to row of dataframe and to fit
        '''
        res  = FitResult.from_json(path = self.__path)
        data = self.__get_info(res = res)

        data.update(self.__meta.model_dump())

        data['comp'   ] = self.dataset
        data['mva_cmb'] = self.__meta.mva_cmb.lower_str
        data['mva_prc'] = self.__meta.mva_prc.lower_str
        data['block'  ] = str(self.__meta.block)   # BaseModel
        data['brem'   ] = self.__meta.brem.region  # Enum -> StrEnum

        return data
    # -------------------------------
    def __get_info(self, res : FitResult) -> dict[str,float|str]:
        '''
        Parameters
        -------------
        res  : Fit result

        Returns
        -------------
        Dictionary representing a row in the dataframe
        '''
        data : dict[str,float|str] = {}
        for par in res.parameters:
            data[f'{par.name}_value'] = par.value
            data[f'{par.name}_error'] = par.error

        if self.__skip_brem_info(res = res):
            pass
        elif self.dataset.is_mc: 
            mc_brem_info = self.__get_mc_brem_info(path = self.__path)
            data.update(mc_brem_info)
        else:
            dt_brem_info = self.__get_dt_brem_info(res = res)
            data.update(dt_brem_info)

        if res.gof is None:
            data['pvalue_value'] = -1 
            data['pvalue_error'] =  0 
        else:
            data['pvalue_value'] =  res.gof.pval 
            data['pvalue_error'] =  0.1

        return data
    # ----------------------
    def __skip_brem_info(self, res : FitResult) -> bool:
        '''
        Parameters
        ------------
        res: Object holding results of fit

        Returns
        ------------
        True if yields per brem fraction won't be extracted
        e.g. for the muon channel or when fits are not done per brem category 
        '''
        if self.__meta.channel == Channel.mm:
            return True

        # NOTE: If fit is not per-brem, fraction won't exist
        # therefore, skip brem info extraction
        for comp in Component:
            brem_fraction = f'{comp}_fraction' 
            if brem_fraction in res:
                return False

        return True 
    # ----------------------
    def __get_dt_brem_info(self, res : FitResult) -> dict[str,float]:
        fraction       = f'{self.signal}_fraction'
        fr_val, fr_err = res[fraction]

        data : dict[str,float] = dict()
        data[f'{self.signal}_fraction_{Brem.one}_value'] = fr_val
        data[f'{self.signal}_fraction_{Brem.one}_error'] = fr_err

        data[f'{self.signal}_fraction_{Brem.two}_value'] = 1 - fr_val
        data[f'{self.signal}_fraction_{Brem.two}_error'] =     fr_err

        # WARNING: rk and rkst fits seem to use different naming
        # for signal yields of combined category
        total_yield_1 = f'yld_{self.signal}_{Brem.brx12}'
        total_yield_2 = f'yld_{self.signal}'
        if total_yield_1 in res:
            yl_val, yl_err = res[total_yield_1]
        else:
            yl_val, yl_err = res[total_yield_2]

            data[f'yld_{self.signal}_{Brem.brx12}_value'] = yl_val 
            data[f'yld_{self.signal}_{Brem.brx12}_error'] = yl_err 

        frc = gvar(fr_val, fr_err)
        yld = gvar(yl_val, yl_err)
        yld_1 = yld * frc
        yld_2 = yld - yld_1 

        data[f'yld_{self.signal}_{Brem.one}_value'] = yld_1.mean
        data[f'yld_{self.signal}_{Brem.one}_error'] = yld_1.sdev

        data[f'yld_{self.signal}_{Brem.two}_value'] = yld_2.mean
        data[f'yld_{self.signal}_{Brem.two}_error'] = yld_2.sdev

        return data
    # ----------------------
    def __get_mc_brem_info(self, path : Path) -> dict[str,float]:
        '''
        Parameters
        ----------------
        path: Path to `parameters.json` file with fit parameters

        Returns
        ----------------
        Dictionary with information associated to brem (yields, fractions, etc)
        '''
        data : dict[str,float] = {}
        if str(Brem.one) in str(path):
            path_b1  = path
            path_b2  = Path(str(path).replace(str(Brem.one), str(Brem.two)))
        else:
            path_b1  = Path(str(path).replace(str(Brem.two), str(Brem.one)))
            path_b2  = path

        nentries_b1 = self.__get_mc_nentries(path=path_b1)
        nentries_b2 = self.__get_mc_nentries(path=path_b2)

        nentries = nentries_b1 + nentries_b2

        data[f'yld_{self.signal}_brem_x12_value'] = nentries
        data[f'yld_{self.signal}_brem_x12_error'] = math.sqrt(nentries)

        # NOTE: We only store brem 1 fraction, either in brem 1 or brem 2 fits
        data[f'{self.signal}_fraction_value'] = nentries_b1 / nentries
        data[f'{self.signal}_fraction_error'] = math.sqrt(nentries_b1) / nentries

        return data
    # ----------------------
    def __get_mc_nentries(self, path : Path) -> float:
        '''
        This is needed to get entries from simulated datasets

        Parameters
        -------------
        path: Path to YAML file with parameters

        Returns
        -------------
        Number of entries in dataset used in fit
        '''
        log.debug(f'Getting MC entries from: {path}')

        json_path = path.parent / 'data.json'
        if not json_path.exists():
            raise FileNotFoundError(f'Cannot find: {json_path}')

        try:
            df   = pnd.read_json(json_path)
        except Exception as exc:
            raise Exception(f'Cannot build dataframe from {json_path}') from exc

        return len(df)
    # -------------------------------
    @cached_property
    def dataset(self) -> Component:
        '''
        Component representing the dataset been fitted
        '''
        for comp in Component:
            if f'/{comp}/' not in str(self.__path):
                continue

            return comp

        raise ValueError(f'No dataset component found in: {self.__path}')
    # -------------------------------
    @cached_property
    def signal(self) -> Component:
        '''
        Component taken as signal in fit to data or simulation 
        '''
        # In MC fits, sample is also signal component
        if self.dataset.is_mc:
            return self.dataset

        # In data fits there will be a fraction parameter
        # that can be used to read the signal component
        res = FitResult.from_json(path = self.__path)

        for comp in Component:
            fraction_parameter = f'{comp}_fraction'
            if fraction_parameter in res:
                return comp

        raise ValueError(f'Signal not found in result: {res}')
    # -------------------------------
    @property
    def is_valid(self) -> bool:
        '''
        True if path is compatible with valid fit
        '''
        cfg = self.__cfg
        if self.__meta.q2bin not in cfg.root:
            return False

        cfg = cfg.root[self.__meta.q2bin]
        if self.__meta.project not in cfg:
            return False

        cfg = cfg[self.__meta.project]
        if self.__meta.channel not in cfg:
            return False

        comp = cfg[self.__meta.channel]
        if self.dataset != comp and self.dataset.is_mc:
            return False

        return True
    # -------------------------------
    @classmethod
    def from_name(
        cls, 
        kind : str,
        name : str) -> Sequence['FitOutput']:
        '''
        Parameters
        ----------------
        name: Identifier for fit, e.g. reso_dtf-latest
        kind: E.g. rare, reso

        Returns
        ----------------
        List of instances of object wrapping fit output
        '''
        log.info('Looking for paths')

        json_wc  = f'fits/data/{name}/*/{kind}/*/*/*/*/fit/brem_*/brem_*/parameters.json'
        paths    = list(_ANADIR.glob(pattern = json_wc))

        log.info(f'Found {len(paths)} paths')

        data     = gut.load_data(package = 'fitter_data', fpath = f'fit_summary/{kind}.yaml')
        cfg      = FitOutputConf(**data)

        all_objs = [ cls(path = path, cfg = cfg) for path in paths ]

        if not all_objs:
            raise ValueError(f'No JSON files found in: {_ANADIR/json_wc}')

        log.info(f'Made {len(all_objs)} fit objects')

        outputs  = [ obj for obj in all_objs if obj.is_valid ]

        if not outputs:
            raise ValueError('No fit oututs found')

        log.info(f'Found {len(outputs)} fit outputs')

        return outputs
# -------------------------------
class FitSummary:
    '''
    Class meant to aggregate fits and return dataframe with the parameters
    '''
    # ----------------------
    def __init__(self, name : str, kind : str) -> None:
        '''
        Parameters
        -------------
        name: Name of fit, e.g. reso_dtf-latest 
        kind: E.g. rare, reso
        '''
        self.__name = name
        self.__fits : Sequence[FitOutput] = FitOutput.from_name(name = name, kind = kind)
    # ----------------------
    @property
    def fit_dir(self) -> Path:
        '''
        Returns
        -------------
        Absolute path to directory
        '''
        ana_dir = Path(os.environ['ANADIR'])

        fit_dir = ana_dir / f'fits/data/{self.__name}'

        if not fit_dir.exists():
            raise FileNotFoundError(f'Coult not find: {fit_dir}')

        log.info(f'Picking up parameters from directory: {fit_dir}')

        return fit_dir
    # ----------------------
    def get_df(self, force_update : bool = False) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        by_fit      : If True each row represents a fit with all parameters.
                      False would make each parameter a row

        suffix      : Used in naming of output files
        force_update: If true (default false) will regenerate file, otherwise will reuse file if found
        '''
        output_path  = self.fit_dir / 'parameters.parquet'

        if output_path.exists() and not force_update:
            log.info(f'Reading cached files at: {output_path}')
            return pnd.read_parquet(output_path)

        rows : list[dict[str,float|str]] = [ fit_out.info for fit_out in self.__fits ]

        df = pnd.DataFrame(rows)
        df.to_parquet(path = output_path)
        log.info(f'Saving summary to: {output_path}')

        return df
# -------------------------------
