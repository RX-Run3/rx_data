'''
Module holding FitSummary class
'''
import os
import tqdm
import math
import pandas as pnd

from dmu           import LogStore
from dmu.stats     import FitResult

from pathlib       import Path
from typing        import Any, Final
from rx_common     import Brem, Component
from .fit_metadata import FitMetadata

log=LogStore.add_logger('fitter:fit_summary')
# TODO: Generalize tool to deal with any sample, i.e.
# - Generalize _regex to match any sample and pick name
# - For MC, instead of nentries use yld_{sample}
# ----------------------
def _cast(row : pnd.Series) -> pnd.Series:
    to_be_casted : list[str] = [
        'block'    ,
        'brem'     ,
        'mva_cmb'  ,
        'mva_prc'  ,
    ]

    if row.name not in to_be_casted:
        return row

    return row.apply(str)
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
        data  : Component | None,
        signal: Component | None,
        name  : str) -> None:
        '''
        Parameters
        -------------
        data  : Component name associated to data
        signal: Name of signal component needed to find JSON files or None to skip it
        name  : Name of directory in {ANADIR}/fits/data/{name}
        '''
        self._signal  = signal
        self._data    = data
        self._fit_dir = self._get_fit_dir(name=name)

        self._patterns : Final[dict[Component,str]] = {}
        if data:
            self._patterns[data]    = f'*_*_*/*/r*/*/*/{data}/fit/*/brem_*/parameters.json'

        if signal:
             self._patterns[signal] = f'*_*_*/*/r*/*/*/{signal}/fit/brem_*/brem_*/parameters.json'
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
    def _get_parameter_paths(self, comp : Component) -> list[Path]:
        '''
        Parameters
        -------------
        comp: Fit component whose parameters need to be extracted

        Returns
        -------------
        List of paths to JSON files with fitting parameters
        '''
        pattern = self._patterns[comp]
        gen     = self._fit_dir.glob(pattern=pattern)
        files   = list(gen)

        if not files:
            raise ValueError(f'No files found in: {self._fit_dir}/{pattern}')
        else:
            nfile   = len(files)
            log.info(f'Found {nfile} files')

        return files
    # ----------------------
    def _get_data(
        self,
        by_fit : bool,
        comp   : Component,
        path   : Path) -> list[dict[str, float | str]] | list[dict[str, float]]:
        '''
        Parameters
        -------------
        by_fit : If True each row will represent a fit, otherwise each row represents a parameter
        comp   : Component, e.g. data or signal MC 
        path   : Path to JSON file with fit parameters

        Returns
        -------------
        List of dictionaries, each representing a row in the dataframe
        '''
        log.debug(f'Using data from: {path}')
        res = FitResult.from_json(path = path)
        if by_fit:
            data = self._get_data_by_fit(res = res, comp = comp, path = path)
        else:
            data = self._get_data_by_par(res = res, comp = comp, path = path)

        return data
    # ----------------------
    def _get_data_by_fit(
        self,
        path : Path,
        res  : FitResult,
        comp : Component) -> list[dict[str,float]]:
        '''
        Parameters
        -------------
        path   : Path to JSON file with fit parameters
        by_fit : If True each row will represent a fit, otherwise each row represents a parameter
        res    : Fit result

        Returns
        -------------
        List of dictionaries, each representing a row in the dataframe
        '''
        data : dict[str,float] = {}
        for par in res.parameters:
            data[f'{par.name}_value'] = par.value
            data[f'{par.name}_error'] = par.error

        if comp.is_mc:
            mc_brem_info = self._get_mc_brem_info(path = path)
            data.update(mc_brem_info)

        if res.gof is None:
            data['pvalue_value'] = -1 
            data['pvalue_error'] =  0 
        else:
            data['pvalue_value'] =  res.gof.pval 
            data['pvalue_error'] =  0.1

        return [data]
    # ----------------------
    def _get_data_by_par(
        self,
        path : Path,
        res  : FitResult,
        comp : Component) -> list[dict[str,float | str]]:
        '''
        Parameters
        -------------
        path   : Path to JSON file with fit parameters
        by_fit : If True each row will represent a fit, otherwise each row represents a parameter
        res    : Fit result

        Returns
        -------------
        List of dictionaries, each representing a row in the dataframe
        '''
        data : list[dict[str,float | str]] = []

        for par in res.parameters:
            entry : dict[str,float | str] = {
                'Parameter' : par.name,
                'Value'     : par.value,
                'Error'     : par.error,
            }

            data.append(entry)

        if comp.is_mc:
            nentries = self._get_mc_nentries(path=path)
            entry : dict[str,float | str] = {
                'Parameter' : f'yld_{self._signal}',
                'Value'     : nentries,
                'Error'     : math.sqrt(nentries),
            }
            data.append(entry)

        entry : dict[str,float | str]  = {}
        if res.gof is None:
            entry['Parameter'] = 'pvalue'
            entry['Value'    ] = -1 
            entry['Error'    ] =  0 
        else:
            entry['Parameter'] = 'pvalue'
            entry['Value'    ] =  res.gof.pval 
            entry['Error'    ] =  0.1

        data.append(entry)

        return data
    # ----------------------
    def _get_mc_brem_info(self, path : Path) -> dict[str,float]:
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

        nentries_b1 = self._get_mc_nentries(path=path_b1)
        nentries_b2 = self._get_mc_nentries(path=path_b2)

        nentries = nentries_b1 + nentries_b2

        data[f'yld_{self._signal}_brem_x12_value'] = nentries
        data[f'yld_{self._signal}_brem_x12_error'] = math.sqrt(nentries)

        # NOTE: We only store brem 1 fraction, either in brem 1 or brem 2 fits
        data[f'{self._signal}_fraction_value'] = nentries_b1 / nentries
        data[f'{self._signal}_fraction_error'] = math.sqrt(nentries_b1) / nentries

        return data
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
        log.debug(f'Getting MC entries from: {path}')

        json_path = path.parent / 'data.json'
        if not json_path.exists():
            raise FileNotFoundError(f'Cannot find: {json_path}')

        try:
            df   = pnd.read_json(json_path)
        except Exception as exc:
            raise Exception(f'Cannot build dataframe from {json_path}') from exc

        return len(df)
    # ----------------------
    def _get_df(
        self,
        by_fit: bool,
        comp  : Component) -> pnd.DataFrame:
        '''
        Parameters
        -------------
        comp  : Component for which dataframe is needed
        by_fit: If True, each row represents a fit, i.e. all parameters

        Returns
        -------------
        Pandas dataframe with parameters
        '''
        paths = self._get_parameter_paths(comp = comp)
        npath = len(paths)
        log.info(f'Loading {comp} dataframe from {npath} paths')

        l_data : list[dict[str,Any]] = []
        for path in tqdm.tqdm(paths, ascii=' -'):
            meta     = FitMetadata.from_pars_path(
                path = path,
                comp = comp)

            info      = self._get_data(
                by_fit= by_fit,
                path  = path,
                comp  = comp)

            meta_info = {name : getattr(meta,name) for name in meta.model_fields_set}

            for elm in info:
                elm.update(meta_info)

            l_data += info

        df         = pnd.DataFrame(l_data)
        df['comp'] = comp

        return df
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
    def get_df(
        self,
        by_fit       : bool       = True,
        suffix       : str | None = None,
        force_update : bool       = False) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        by_fit      : If True each row represents a fit with all parameters.
                      False would make each parameter a row

        suffix      : Used in naming of output files
        force_update: If true (default false) will regenerate file, otherwise will reuse file if found
        '''
        if suffix is None:
            output_path  = self._fit_dir / 'parameters.parquet'
        else:
            output_path  = self._fit_dir / f'parameters_{suffix}.parquet'

        if output_path.exists() and not force_update:
            log.info(f'Reading cached files at: {output_path}')
            return pnd.read_parquet(output_path)

        l_df : list[pnd.DataFrame] = [ self._get_df(comp = comp, by_fit = by_fit) for comp in [self._data, self._signal] if comp ]
        df = pnd.concat(l_df, axis=0)
        df = df.apply(_cast)
        df = df.reset_index(drop=True)

        self._save_df(df=df, path = output_path)

        return df
# -------------------------------
