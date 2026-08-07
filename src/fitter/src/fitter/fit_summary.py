'''
Module holding FitSummary class
'''
import os
import tqdm

from gvar          import gvar
from dmu           import LogStore
from dmu.stats     import FitParameter, FitResult
from functools     import cached_property
from pathlib       import Path
from typing        import Final
from pydantic      import RootModel
from rx_common     import Component, Channel, Brem

from .fit_metadata import FitMetadata

log=LogStore.add_logger('fitter:fit_summary')

_ANADIR : Final[Path] = Path(os.environ['ANADIR'])
# -------------------------------
class FitHarmonizer:
    '''
    Class meant to equalize fit results between data and simulation
    I.e. fits to simulation and data need the same parameters, this
    class will make sure that it happens
    '''
    # -------------------------------
    def __init__(self, fres : FitResult, meta : FitMetadata):
        '''
        Parameters
        --------------
        fres: Object holding fit result 
        meta: Object holding information on fitted sample
        '''
        self.__fres = fres 
        self.__meta = meta 
    # ----------------------
    def __skip_brem_info(self) -> bool:
        '''
        Returns
        ------------
        True if yields per brem fraction won't be extracted
        e.g. for the muon channel or when fits are not done per brem category 
        '''
        if self.__meta.channel == Channel.mm:
            return True

        # NOTE: If fit is not per-brem, fraction won't exist
        # therefore, skip brem info extraction
        if self.signal is not None:
            return False

        return True 
    # ----------------------
    @cached_property
    def signal(self) -> Component | None:
        '''
        Component used as signal if associated brem fraction
        exists. Otherwise None
        '''
        for comp in Component:
            brem_fraction = f'{comp}_fraction' 
            if brem_fraction in self.__fres:
                return comp 

        return None
    # ----------------------
    def __get_dt_brem_pars(self) -> list[FitParameter]:
        '''
        Returns
        -------------
        List of parameters needed to be added for FitSummary in data
        '''
        signal                    = self.signal
        res                       = self.__fres
        pars : list[FitParameter] = []

        fraction       = f'{signal}_fraction'
        fr_val, fr_err = res[fraction]

        pars.append(FitParameter(name = f'{signal}_fraction_{Brem.one}', value =     fr_val, error = fr_err))
        pars.append(FitParameter(name = f'{signal}_fraction_{Brem.two}', value = 1 - fr_val, error = fr_err))

        # WARNING: rk and rkst fits seem to use different naming
        # for signal yields of combined category
        total_yield_1 = f'yld_{signal}_{Brem.brx12}'
        total_yield_2 = f'yld_{signal}'
        if total_yield_1 in res:
            yld_val, yld_err = res[total_yield_1]
        else:
            yld_val, yld_err = res[total_yield_2]

        frc = gvar(fr_val, fr_err)
        yld = gvar(yld_val, yld_err)
        yld_1 = yld * frc
        yld_2 = yld - yld_1 

        pars.append(FitParameter(name = f'yld_{signal}_{Brem.one}'  , value = yld_1.mean, error = yld_1.sdev))
        pars.append(FitParameter(name = f'yld_{signal}_{Brem.two}'  , value = yld_2.mean, error = yld_2.sdev))

        if total_yield_1 not in res:
            pars.append(FitParameter(name = f'yld_{signal}_{Brem.brx12}', value = yld_val   , error = yld_err   ))

        return pars 
    # ----------------------
    def __get_mc_brem_pars(self) -> list[FitParameter]:
        '''
        Returns
        ----------------
        Dictionary with information associated to brem (yields, fractions, etc)
        '''
        comp     = self.__meta.component
        brem     = self.__meta.brem
        val, err = self.__meta.stats

        par = FitParameter(name = f'yld_{comp}_{brem}', value = val, error = err)

        return [par]
    # -------------------------------
    def get_result(self) -> FitResult: 
        '''
        Returns
        -------------
        FitResult after harmonization
        '''
        if self.__skip_brem_info():
            return self.__fres

        pars : list[FitParameter] = []
        if self.__meta.component.is_mc: 
            pars = self.__get_mc_brem_pars()
        else:
            pars = self.__get_dt_brem_pars()

        try:
            fres = self.__fres.extend(pars = pars)
        except Exception as exc:
            log.error(self.__fres)
            log.error(self.__meta)
            raise ValueError('Cannot extend fit result') from exc

        return fres
# -------------------------------
class FitSummary(RootModel[list[tuple[FitMetadata,FitResult]]]):
    '''
    Class representing a collection of fit results
    '''
    # -----------------
    def at(self, meta : FitMetadata) -> FitResult:
        '''
        Parameters
        ---------------
        meta: Object holding fit metadata

        Returns
        ---------------
        Fit result corresponding to metadata
        '''
        return self.__as_dict[meta]
    # -----------------
    @cached_property
    def __as_dict(self) -> dict[FitMetadata,FitResult]:
        '''
        Dictionary version of fit summary, used to query entries
        '''
        return dict(self.root)
    # -----------------
    def __str__(self):
        msg = '\n'
        for meta, _ in self.root:
            msg += f'{meta.as_str}\n'

        return msg
    # -----------------
    @classmethod
    def from_json(cls, path : Path) -> 'FitSummary':
        '''
        Parameters
        -------------
        path: Path to JSON file with serialized FitSummary
        '''
        string = path.read_text()

        return cls.model_validate_json(json_data = string)
    # -----------------
    def to_json(self, path : Path) -> None:
        '''
        Parameters
        ----------------
        path: Path to JSON file
        '''
        path.parent.mkdir(exist_ok=True, parents=True)

        log.info(f'Saving fit summary to: {path}')

        string = self.model_dump_json(indent = 2)
        path.write_text(string)
# -------------------------------
class FitSummarizer:
    '''
    Class meant to aggregate fits and return FitSummary 
    '''
    # ----------------------
    def __init__(self, name : str, kind : str) -> None:
        '''
        Parameters
        -------------FitHarmoniFitHarmonizer
        name: Name of fit, e.g. reso_dtf-latest 
        kind: E.g. rare, reso
        '''
        self.__name = name
        self.__kind = kind
    # ----------------------
    def __get_paths(self) -> list[Path]:
        '''
        Returns
        --------------
        List of paths to parameters.json files storing fits
        '''
        log.info('Looking for paths')

        json_wc  = f'fits/data/{self.__name}/*/{self.__kind}/*/*/*/*/fit/brem_*/brem_*/parameters.json'
        paths    = list(_ANADIR.glob(pattern = json_wc))

        log.info(f'Found {len(paths)} paths')

        return paths
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
    def get_summary(self, force_update : bool = False) -> FitSummary:
        '''
        Parameters
        ---------------
        force_update: If true (default false) will regenerate file, otherwise will reuse file if found
        '''
        output_path  = self.fit_dir / 'fit_summary.json'

        if output_path.exists() and not force_update:
            log.info(f'Reading cached files at: {output_path}')
            return FitSummary.from_json(path = output_path)

        fits : list[tuple[FitMetadata,FitResult]] = [] 

        paths = self.__get_paths()

        log.info('Building summary')
        for path in tqdm.tqdm(paths, ascii = ' -'):
            meta = FitMetadata.from_pars_path(path = path)
            fres = FitResult.from_json(path = path)

            hrm  = FitHarmonizer(fres = fres, meta = meta)
            fres = hrm.get_result()
            fits.append((meta, fres))

        summary = FitSummary(root = fits) 
        summary.to_json(path = output_path)

        return summary
# -------------------------------
