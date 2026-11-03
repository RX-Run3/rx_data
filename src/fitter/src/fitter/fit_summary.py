'''
Module holding FitSummary class
'''
import os
import tqdm

from gvar          import GVar, gvar
from dmu           import LogStore
from dmu.stats     import FitParameter, FitResult
from functools     import cached_property
from pathlib       import Path
from typing        import Any, Final
from pydantic      import RootModel
from rx_common     import Block, Component, Channel, Brem

from .yields       import Yield, YieldGrid
from .fit_metadata import FitMetadata

log=LogStore.add_logger('fitter:fit_summary')

_ANADIR    : Final[Path] = Path(os.environ['ANADIR'])
_DSET_SIZE : Final[str ] = 'yld_all'
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
            log.debug('Skipping brem info')
            return True

        # NOTE: {SIGNAL}_fraction will exist if fit was done simultaneously
        # in brem categories
        brem_fraction = f'{self.__meta.signal}_fraction'
        if brem_fraction in self.__fres:
            return False

        log.debug('Skipping brem info')
        return True
    # ----------------------
    def __get_dt_brem_pars(self) -> list[FitParameter]:
        '''
        Returns
        -------------
        List of brem related parameters needed for FitSummary in data
        '''
        if self.__meta.component.is_mc:
            return []

        if self.__skip_brem_info():
            return []

        signal                    = self.__meta.signal
        res                       = self.__fres
        pars : list[FitParameter] = []

        fraction       = f'{signal}_fraction'
        fr_val, fr_err = res[fraction]

        pars.append(FitParameter(name = f'fr_{signal}_{Brem.one}', value =     fr_val, error = fr_err))
        pars.append(FitParameter(name = f'fr_{signal}_{Brem.two}', value = 1 - fr_val, error = fr_err))

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

        proj = self.__meta.project
        pars.append(FitParameter(name = f'yld_{signal}_{proj}_{Brem.one}', value = yld_1.mean, error = yld_1.sdev))
        pars.append(FitParameter(name = f'yld_{signal}_{proj}_{Brem.two}', value = yld_2.mean, error = yld_2.sdev))

        if total_yield_1 not in res:
            pars.append(FitParameter(name = f'yld_{signal}_{proj}_{Brem.brx12}', value = yld_val, error = yld_err))

        return pars
    # ----------------------
    def __get_dt_yield_pars(self) -> list[FitParameter]:
        '''
        Returns
        -------------
        Yield parameters calculated from e.g. scales
        '''
        yield_pars : list[FitParameter] = []

        if self.__meta.component.is_mc:
            return yield_pars

        val, err = self.__meta.stats
        par = FitParameter(name = _DSET_SIZE, value = val, error = err)
        yield_pars.append(par)

        signal = self.__meta.signal
        log.debug(f'Using signal {signal} to add scaled yield parameters in data')
        scales = self.__fres.get_pars(prefix = 's_')
        if not scales:
            log.debug('No scales found, no extra yield parameters calculated')
            return yield_pars

        fit_pars = self.__fres.get_pars(prefix = f'yld_{signal}')
        if len(yield_pars) != 1:
            log.error(self.__fres)
            raise ValueError(f'Not found one and only one signal ({signal}) parameter: {yield_pars}')

        sig_par = fit_pars[0]

        for scale in scales:
            par     = scale * sig_par
            nopref  = scale.name.removeprefix('s_')
            new_par = par.model_copy(update = {'name' : f'yld_{nopref}'})

            log.debug(f'Adding {new_par.name}')

            yield_pars.append(new_par)

        return yield_pars
    # ----------------------
    def __get_mc_brem_pars(self) -> list[FitParameter]:
        '''
        Returns
        ----------------
        Dictionary with information associated to brem (yields, fractions, etc)
        '''
        if not self.__meta.component.is_mc:
            return []

        if self.__skip_brem_info():
            return []

        log.debug('Adding MC brem parameters')

        comp     = self.__meta.component
        brem     = self.__meta.brem
        proj     = self.__meta.project
        val, err = self.__meta.stats

        par = FitParameter(name = f'yld_{comp}_{proj}_{brem}', value = val, error = err)

        return [par]
    # -------------------------------
    def get_result(self) -> FitResult:
        '''
        Returns
        -------------
        FitResult after harmonization
        '''
        pars : list[FitParameter] = []

        pars += self.__get_mc_brem_pars()
        pars += self.__get_dt_brem_pars()
        pars += self.__get_dt_yield_pars()

        try:
            fres = self.__fres.extend(pars = pars)
        except Exception as exc:
            log.error(self.__fres)
            log.error(self.__meta)
            raise ValueError('Cannot extend fit result') from exc

        return fres
# -------------------------------
class FitSummary(RootModel[list[tuple[FitMetadata,FitResult]]], frozen = True):
    '''
    Class representing a collection of fit results
    '''
    # ----------------------
    def split(self, by : str) -> list['FitSummary']:
        '''
        Parameters
        -------------------
        by: Name of field in FitMetadata

        Returns
        -------------------
        List of FitSummary objects where only the attribute passed
        differs
        '''
        if by not in FitMetadata.model_fields:
            raise ValueError(f'Field {by} not in FieldMetadata')

        data : dict[str, list[tuple[FitMetadata,FitResult]]] = dict()

        for meta, fsmr in self.root:
            hsh = meta.weak_hash(exclude = by)
            elm = meta, fsmr

            if hsh not in data:
                data[hsh] = [elm]
            else:
                data[hsh].append(elm)

        return [ FitSummary(root = elements) for elements in data.values() ]
    # ----------------------
    @classmethod
    def merge(cls, summaries : list['FitSummary']) -> 'FitSummary':
        '''
        Parameters
        --------------
        summaries: List of fit summaries

        Returns
        --------------
        Merged fit summaries
        '''
        data : list[tuple[FitMetadata, FitResult]] = []

        for summary in summaries:
            data.extend(summary.root)

        return cls(root = data)
    # ----------------------
    def get_fitted_yields(self, exclude : Component | None = None) -> list[str]:
        '''
        Parameters
        ----------------
        exclude: Name of component whose yield will be excluded, e.g. `..._{COMPONENT}_...`

        Returns
        ----------------
        List of names of yields in fits
        '''
        names : set[str] = set()
        for _, result in self.root:
            pars = result.get_pars(prefix = 'yld')
            names= names | { par.name for par in pars if par.name != _DSET_SIZE } # Exclude yld_all, which is a yield, but not from fit

        if exclude is None:
            return list(names)

        return [ name for name in names if f'_{exclude}_' not in name ]
    # ----------------------
    def make_grid(self, var : str, fall_back : float | None) -> YieldGrid:
        '''
        Parameters
        --------------------
        var      : Name of variable in FitResult objects for Z axis
        fall_back: Value used if value is missing in any grid point
                   If None, will raise exception when value is missing

        Returns
        --------------------
        Grid of yields for passed variable,
        '''
        nodes = []
        for meta, fres in self.root:
            zval, zerr = fres.get(name = var, fall_back = fall_back)

            yld     = Yield(
                val = zval,
                err = zerr,
                wp  = meta.wp)

            nodes.append(yld)

        grid = YieldGrid(root = nodes)

        return grid
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
        key = hash(meta)
        if key in self.__as_dict:
            return self.__as_dict[key]

        summary = self
        for name, value in meta.fields:
            tmp = summary.query(name = name, value = value)
            if not tmp.root:
                log.warning(f'Failed: {name} = {value}')
                log.warning(summary)
            else:
                log.info(f'Filtered by: {name} = {value}')
                log.info(tmp)

            summary = tmp

        if len(summary.root) == 1:
            [(meta_summary, _)] = summary.root

            log.error(meta_summary)
            log.error(meta)
            log.error(f'{hash(meta)} != {hash(meta_summary)}')
            raise KeyError('Entries do not match')

        log.error(meta)
        raise KeyError('Cannot read summary')
    # -----------------
    def query(self, name : str, value : Any) -> 'FitSummary':
        '''
        Parameters
        ---------------
        name : Name of field
        value: Value of field

        Returns
        ---------------
        Summary containing only given value of field in metadata
        '''
        filtered_data = [ (meta, fres) for meta, fres in self.root if getattr(meta, name) == value ]

        return FitSummary(root = filtered_data)
    # -----------------
    @cached_property
    def __as_dict(self) -> dict[int,FitResult]:
        '''
        Dictionary mapping metadata hash to fitresult
        '''
        data = { hash(meta) : fres for meta, fres in self.root }

        return data
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
class SummaryProcessor:
    '''
    Class meant to process fit summaries
    '''
    # -------------------------------
    def __init__(self, summary : FitSummary):
        '''
        Parameters
        -----------------
        summary: Object storing fit summary
        '''
        self.__summary = summary
    # -------------------------------
    def _process_blocks(self, summary : FitSummary) -> FitSummary:
        '''
        Parameters
        ---------------
        summary: Fit summary where fits differ by only block
        '''
        yields : dict[Block,GVar] = dict()

        meta, _ = summary.root[0]

        if meta.component.is_mc:
            return summary

        signal  = meta.signal
        brem    = meta.brem
        proj    = meta.project
        total   = gvar(0, 0)

        # NOTE: Below the new and old naming are needed due to
        # the introduction of the project as part of the parameter name
        # which is needed in order to build simulteneous fit likelihoods
        for meta, fres in summary.root:
            old_name = f'yld_{signal}_{brem}'
            vals     = fres.opt_get(name = old_name)

            if vals is None:
                new_name = f'yld_{signal}_{proj}_{brem}'
                vals     = fres.opt_get(name = new_name)

            if vals is None:
                log.error(meta)
                raise ValueError('Cannot add block fractions')

            val, err           = vals
            element            = gvar(val, err)
            yields[meta.block] = element

            total = total + element

        fractions  = { block : block_yield / total for block, block_yield in yields.items() }
        parameters = { block : FitParameter(name = f'bk_{signal}_{brem}', value = fr.mean, error = fr.sdev) for block, fr in fractions.items() }

        data : list[tuple[FitMetadata, FitResult]] = []
        for meta, fres in summary.root:
            param    = parameters[meta.block]
            new_fres = fres.extend(pars = [param])

            data.append((meta, new_fres))

        return FitSummary(root = data)
    # -------------------------------
    def _process_brems(self, summary : FitSummary) -> FitSummary:
        '''
        Parameters
        --------------------
        summary: Holder of identical fits, but different brem categories

        Returns
        --------------------
        Summary with brem information added for MC, data will do early return
        '''
        any_meta, _ = summary.root[0] # All elements are identical, except for brem

        if not any_meta.component.is_mc:
            return summary

        if any_meta.channel != Channel.ee:
            return summary

        tot = gvar(0, 0)
        yields : dict[Brem,GVar] = dict()
        for meta, _ in summary.root:
            val, err = meta.stats
            yld      = gvar(val, err)
            tot      = tot + yld

            yields[meta.brem] = yld

        fractions : dict[Brem,GVar] = { brem : yld / tot for brem, yld in yields.items() }

        elements : list[tuple[FitMetadata,FitResult]] = []
        for meta, fres in summary.root:
            fr            = fractions[meta.brem]
            par           = FitParameter(name = f'fr_{meta.signal}_{meta.brem}', value = fr.mean, error = fr.sdev)
            extended_fres = fres.extend(pars = [par])

            elements.append((meta, extended_fres))

        return FitSummary(root = elements)
    # -------------------------------
    def run(self) -> FitSummary:
        '''
        Returns
        ---------------
        Processed summary object
        '''
        summaries = self.__summary.split(by = 'block')
        summaries = [ self._process_blocks(summary = summary) for summary in summaries ]

        merged    = FitSummary.merge(summaries = summaries)

        summaries = merged.split(by = 'brem')
        summaries = [ self._process_brems(summary = summary) for summary in summaries ]

        return FitSummary.merge(summaries = summaries)
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
        self.__out_name : str | None = None
    # ----------------------
    @property
    def out_name(self) -> str | None:
        """The out_name property."""
        return self.__out_name
    # ----------------------
    @out_name.setter
    def out_name(self, value : str):
        if self.__out_name:
            raise ValueError(f'out_name already set as: {self.__out_name}')

        self.__out_name = value
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
    @property
    def output_path(self) -> Path | None:
        '''
        Full path to JSON file where summary will be saved
        if no file name specified, return None
        '''
        if not self.out_name:
            return None

        return self.fit_dir / self.out_name
    # ---------------------------------
    def get_summary(
        self,
        out_name     : str | None = None,
        force_update : bool       = False) -> FitSummary:
        '''
        Parameters
        ---------------
        out_name    : If specified, will save JSON file with summary there
        force_update: If true (default false) will regenerate file, otherwise will reuse file if found
        '''
        if out_name:
            self.out_name = out_name

        if self.output_path and self.output_path.exists() and not force_update:
            log.info(f'Reading cached files at: {self.output_path}')
            return FitSummary.from_json(path = self.output_path)

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

        prc     = SummaryProcessor(summary = summary)
        summary = prc.run()

        if self.output_path:
            summary.to_json(path = self.output_path)

        return summary
# -------------------------------
