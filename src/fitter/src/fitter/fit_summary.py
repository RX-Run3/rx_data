'''
Module holding FitSummary class
'''
import os
import re
import tqdm
import math
import pandas as pnd

from dmu         import LogStore
from dmu.stats   import FitResult

from pathlib     import Path
from typing      import Final
from rx_common   import Brem, Component

log=LogStore.add_logger('fitter:fit_summary')
# TODO: Generalize tool to deal with any sample, i.e.
# - Generalize _regex to match any sample and pick name
# - For MC, instead of nentries use yld_{sample}
# -------------------------------
class FitSummary:
    '''
    Class meant to: 

    - Collect yields an brem fractions from fits
    - Plot yields and fractions
    - Store information in JSON for further usage
    '''
    # ----------------------
    def __init__(
        self, 
        signal: Component,
        name  : str) -> None:
        '''
        Parameters
        -------------
        signal: Name of signal component, e.g. jpsi, needed to find JSON files
        name  : Name of directory in {ANADIR}/fits/data/{name}
        '''
        self._signal  = signal
        self._fit_dir = self._get_fit_dir(name=name)

        dat_regex = r'(\d{3})_(\d{3})_b(\d)/reso/(rk|rkst)/(mm|ee)/(psi2|jpsi)/data_24/fit/.*/brem_([x,0-9]{3})/parameters.json'
        sim_regex = fr'(\d{{3}})_(\d{{3}})_b(\d)/reso/(rk|rkst)/(mm|ee)/(psi2|jpsi)/{signal}/fit/brem_([x,0-9]{{3}})/main_brem_[x,0-9]{{3}}_b\d/parameters.json'

        dat_pattern = '*_*_b*/reso/r*/*/jpsi/data_24/fit/*/brem_*/parameters.json'
        sim_pattern =f'*_*_b*/reso/r*/*/jpsi/{signal}/fit/brem_*/main_brem_*/parameters.json'

        self._patterns : Final[dict[str,str]]  = {'dat' : dat_pattern, 'sim' : sim_pattern}
        self._regexes  : Final[dict[str,str]]  = {'dat' : dat_regex  , 'sim' : sim_regex  }
    # ----------------------
    def _get_fit_dir(self, name : str) -> Path:
        '''
        Parameters
        -------------
        name: Name of directory with fits

        Returns
        -------------
        Absolute path to directory
        '''
        ana_dir = Path(os.environ['ANADIR'])

        fit_dir = ana_dir / f'fits/data/{name}'

        if not fit_dir.exists():
            raise FileNotFoundError(f'Coult not find: {fit_dir}')

        log.info(f'Picking up parameters from directory: {fit_dir}')

        return fit_dir
    # ----------------------
    def _get_parameter_paths(self, kind : str) -> list[Path]:
        '''
        Parameters
        -------------
        kind: dat or sim 

        Returns
        -------------
        List of paths to JSON files with fitting parameters
        '''
        pattern = self._patterns[kind]
        gen     = self._fit_dir.glob(pattern=pattern)
        files   = list(gen)

        if not files:
            raise ValueError(f'No files found in: {self._fit_dir}/{pattern}')
        else:
            nfile   = len(files)
            log.info(f'Found {nfile} files')

        return files
    # ----------------------
    def _extra_information(
        self, 
        kind : str,
        path : Path) -> dict[str, str | Brem]:
        '''
        Parameters
        -------------
        kind : dat or sim 
        path : Path to JSON file with this information

        Returns
        -------------
        Dictionary with non-numerical data, key is meant to be column name
        e.g. brem, block, etc
        '''
        regex = self._regexes[kind]
        mtch  = re.match(f'.*/{regex}', str(path))
        if not mtch:
            raise ValueError(f'Cannot match pattern \"{regex}\" to \"{path}\"')

        groups : list[str] = list(mtch.groups())
        channel            = groups[4]

        data : dict[str, str | Brem] = dict()
        data['mva_cmb'] = groups[0]
        data['mva_prc'] = groups[1]
        data['block'  ] = groups[2]
        data['project'] = groups[3]
        data['channel'] = channel

        if   kind == 'dat':
            data['q2bin'  ] = groups[5]
            data['brem'   ] = str(Brem.from_str(value = groups[6]))
        elif kind == 'sim':
            data['q2bin'  ] = groups[5]
            data['brem'   ] = str(Brem.from_str(value = groups[6]))
        else:
            raise ValueError(f'Invalid kind: {kind}')

        return data
    # ----------------------
    def _get_data(
        self, 
        brem : Brem,
        kind : str,
        path : Path) -> tuple[dict[str, float], dict[str, str | Brem]]:
        '''
        Parameters
        -------------
        brem : Brem for which file is read
        kind : dat or sim 
        path : Path to JSON file with fit parameters

        Returns
        -------------
        Dictionary mapping quantity and value, error or name for e.g. channel.
        '''
        log.debug(f'Using data from: {path}')
        res = FitResult.from_json(path = path)

        data : dict[str,float] = {}
        for par in res.parameters:
            if   par.name == 'jpsi_fraction':
                name = f'{self._signal}_fraction'
            elif par.name == f'yld_{self._signal}' or brem.in_string(string = par.name):
                name = par.name
            else:
                continue

            data[f'{name}_value'] = par.value
            data[f'{name}_error'] = par.error 

        if kind == 'sim':
            data['nentries_value'] = self._get_mc_nentries(path=path)

        meta = self._extra_information(path=path, kind=kind)

        return data, meta
    # ----------------------
    def _get_mc_nentries(self, path : Path) -> float:
        '''
        This is needed to get entries from simulated datasets

        Parameters
        -------------
        path: Path to YAML file with parameters

        Returns
        -------------
        Number of entries in dataset used in fit
        '''
        json_path = path.parent / 'data.json'
        if not json_path.exists():
            raise FileNotFoundError(f'Cannot find: {json_path}')

        try:
            df   = pnd.read_json(json_path)
        except Exception as exc:
            raise Exception(f'Cannot build dataframe from {json_path}') from exc

        return len(df)
    # ----------------------
    def _brem_2_from_1(self, path : Path) -> Path | None:
        '''
        Parameters
        -------------
        path: Path to brem 1 parameters.json

        Returns
        -------------
        None if input path belongs to brem 2 already
        Path to brem 2 if input path belongs to brem 1
        '''
        dat_end_1 = 'brem_xx1/parameters.json'
        dat_end_2 = 'brem_xx2/parameters.json'
        sim_end_1 =r'brem_xx1/main_brem_xx1_b(\d)/parameters.json'
        sim_end_2 =r'brem_xx2/main_brem_xx2_b(\d)/parameters.json'

        value = str(path)
        if value.endswith(dat_end_2):
            return None

        if re.search(sim_end_2, value):
            return None
        
        if value.endswith(dat_end_1):
            value = value.replace(dat_end_1, dat_end_2)
            return Path(value)

        if re.search(sim_end_1, value):
            value = re.sub(sim_end_1, r'brem_xx2/main_brem_xx2_b\1/parameters.json', value)
            return Path(value)

        raise ValueError(f'Cannot replace brem in: {path}')
    # ----------------------
    def _get_df(self, kind : str) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        kind: dat or sim, used to pick input JSON files

        Returns
        -------------
        Pandas dataframe with parameters
        '''
        paths = self._get_parameter_paths(kind = kind)

        l_data : list[dict[str, float | str | Brem ]] = []
        for path_brem_1 in tqdm.tqdm(paths, ascii=' -'):
            path_brem_2 = self._brem_2_from_1(path = path_brem_1)
            if path_brem_2 is None: 
                continue

            data_1, meta_1 = self._get_data(
                brem = Brem.one,
                path = path_brem_1, 
                kind = kind)
            data_2, meta_2 = self._get_data(
                brem = Brem.two,
                path = path_brem_2, 
                kind = kind)

            if kind == 'sim':
                data_1, data_2 = self._post_process_mc(
                    val_1 = data_1,
                    val_2 = data_2)

            info_1 = dict(**data_1, **meta_1)
            info_2 = dict(**data_2, **meta_2)

            l_data.append(info_1)
            l_data.append(info_2)

        df         = pnd.DataFrame(l_data)
        df['kind'] = kind

        return df
    # ----------------------
    def _post_process_mc(
        self, 
        val_1 : dict[str, float ],
        val_2 : dict[str, float ]) -> tuple[dict[str,float], dict[str, float]]:
        '''
        Parameters
        -------------
        val_x : Dictionary with fitting parameters for given fit, or other identifier, for brem 'x'

        Returns
        -------------
        Same as input, but with nentries_value/error keys replaced with fraction_value/error
        '''
        nentries_001 = val_1['nentries_value']
        nentries_002 = val_2['nentries_value']

        ntotal   = nentries_001 + nentries_002
        fraction = nentries_001 / ntotal 
        error    = math.sqrt( fraction * (1 - fraction) / ntotal )

        del val_1['nentries_value']
        del val_2['nentries_value']

        val_1[f'{self._signal}_fraction_value'] = fraction
        val_2[f'{self._signal}_fraction_value'] = fraction

        val_1[f'{self._signal}_fraction_error'] = error 
        val_2[f'{self._signal}_fraction_error'] = error 

        return val_1, val_2 
    # ----------------------
    def _save_df(
        self, 
        df   : pnd.DataFrame, 
        path : Path) -> None:
        '''
        Parameters
        ----------------
        path: Path to parquet file to save
        '''
        df.to_parquet(path = path)
        log.info(f'Saving summary to: {path}')

        str_path = str(path)
        str_path = str_path.replace('.parquet', '.md')
        path     = Path(str_path)
        df.to_markdown(buf = path)

        log.info(f'Saving summary to: {path}')
    # ----------------------
    def get_df(self, force_update : bool = False) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        force_update: If true (default false) will regenerate file, otherwise will reuse file if found 
        '''
        output_path  = self._fit_dir / 'parameters.parquet'
        if output_path.exists() and not force_update:
            log.info(f'Reading cached files at: {output_path}')
            return pnd.read_parquet(output_path)

        df_dat = self._get_df(kind = 'dat')
        df_sim = self._get_df(kind = 'sim')

        df     = pnd.concat([df_dat, df_sim], axis=0)
        df     = df.reset_index(drop=True)
        df     = df.astype(dtype = {'block' : int})

        self._save_df(df=df, path = output_path)

        return df
# -------------------------------
