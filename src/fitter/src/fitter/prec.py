'''
Module containing PRec
'''
import numpy
import slugify
import pandas            as pnd
import matplotlib.pyplot as plt

from functools             import cached_property
from ROOT                  import RDF
from typing                import Final
from pathlib               import Path
from pydantic              import BaseModel, model_validator, ConfigDict

from dmu                   import LogLevels, LogStore
from dmu.generic           import hashing
from dmu.stats             import KDEConf
from dmu.stats             import zfit
from dmu.stats             import ZFitPlotter 
from dmu.stats             import is_pdf_usable
from dmu.stats             import utilities as sut
from dmu.rdataframe        import utilities as rut
from dmu.generic           import utilities as gut
from dmu.workflow          import Cache

from zfit                  import Space         as zobs
from zfit.pdf              import KDE1DimFFT, SumPDF

from rx_data               import RDFGetter
from rx_common             import Component, Cuts, Qsq, Trigger, Mass, CCbarComponent
from rx_selection          import selection     as sel

from .configs                  import CCbarConf, CCbarWeight
from .inclusive_decays_weights import read_weight 
from .inclusive_sample_weights import Reader as SampleWeightReader

log=LogStore.add_logger('fitter:prec')

_KDEPDF                            = KDE1DimFFT
_MIN_ENTRIES    : Final[int]       =  40 # Will not build KDE if fewer entries than this are found
_MODEL_ATTRS    : Final[list[str]] = ['mass', 'wgt', 'dec', 'sam']
_MASSES         : Final[list[str]] = ['B_M', 'B_Mass', 'B_Mass_smr', 'B_const_mass_M', 'B_const_mass_psi2S_M']
_MERGED_PDFNAME : Final[str]       = 'ccbar' # Name of KDE built from adding all candidates in a single dataset
#-----------------------------------------------------------
class CharmoniumComponent(BaseModel, frozen = True):
    '''
    Class meant to represent a single charmonium component
    '''
    model_config = ConfigDict(arbitrary_types_allowed = True)

    name: str
    cfg : KDEConf 
    obs : zobs
    '''
    Normalization observable
    '''
    mass: numpy.ndarray
    wgt : numpy.ndarray # Full weight
    sam : numpy.ndarray # Sample weights
    dec : numpy.ndarray # Weights for individual decays in cocktail
    # ------------------------------
    @cached_property
    def pdf(self) -> _KDEPDF | None:
        '''
        Returns
        ---------------
        Zfit PDF if there are enough entries to build it, otherwise, None
        '''
        if log.getEffectiveLevel() < LogLevels.info:
            log.debug('Using fitting options:')
            log.debug(self.cfg)

        if self.nentries < _MIN_ENTRIES:
            return

        pdf = _KDEPDF(
            name      = self.name,
            norm      = self.obs,
            obs       = self._extended_obs,
            data      = self.mass,
            weights   = self.wgt, 
            padding   = self.cfg.padding.value,
            bandwidth = self.cfg.bandwidth)

        if not is_pdf_usable(pdf = pdf):
            raise ValueError('PDF is not usable')

        return pdf
    # ---------------------------
    @property
    def _extended_obs(self) -> zobs:
        '''
        Observable used to build KDE, defined where data exists
        '''
        if len(self.mass) < _MIN_ENTRIES:
            log.debug('For small dataset, reusing default observable as normalization observable')
            return self.obs

        min_obs = numpy.min(self.mass)
        max_obs = numpy.max(self.mass)

        limits  = min_obs, max_obs

        obs = zfit.Space(
            obs   = self.obs.obs, 
            label = self.obs.label,
            limits= limits)

        return obs
    # ------------------------------
    def get_pdf(self) -> _KDEPDF:
        '''
        Returns PDF or raises if PDF not found
        '''
        if self.pdf is None:
            raise ValueError(f'PDF not made with {self.nentries} entries')

        return self.pdf
    # ------------------------------
    @property
    def nentries(self) -> int:
        '''
        Returns 
        ------------
        Number of entries in observable range
        '''
        lo, hi = sut.range_from_obs(obs = self.obs)

        nentries = numpy.sum((self.mass > lo) & (self.mass < hi))

        return int(nentries)
# ------------------------------
class CCbarModel(BaseModel, frozen = True):
    '''
    Class meant to represent PDF meant to model all the charmonium components 
    '''
    model_config = ConfigDict(arbitrary_types_allowed = True)
    # -------------------------
    name      : str
    obs       : zobs
    '''
    Normalization observable
    '''
    models    : list[CharmoniumComponent] 
    fractions : list[float]
    # -------------------------
    @property
    def is_empty(self) -> bool:
        '''
        True if no component models were created
        '''
        return len(self.models) == 0
    # -------------------------
    @model_validator(mode = 'after')
    def check_sizes(self):
        if len(self.models) != len(self.fractions):
            raise ValueError('Fractions and models differ in number')

        if not self.fractions:
            return self

        unity = sum(self.fractions)
        if not numpy.isclose(unity, 1):
            raise ValueError(f'Fractions do not add up to 1: {self.fractions}')

        positive = all(fraction > 0 for fraction in self.fractions)
        if not positive:
            raise ValueError(f'Not all fractions are positive: {self.fractions}')

        return self
    # -------------------------
    @cached_property
    def pdf(self) -> SumPDF | _KDEPDF | None:
        '''
        Returns
        -----------------
        Either:

        - Full PDF
        - Single component PDF when only one survives
        - None if no model could be built
        '''
        pdfs = [ model.pdf for model in self.models if model.pdf is not None ]

        if not pdfs:
            return

        if len(pdfs) == 1:
            kde      = pdfs[0]
            kde_copy = kde.copy(
                name      = self.name,
                bandwidth = kde._bandwidth, # type: ignore
                data      = kde._data)      # type: ignore see: https://github.com/zfit/zfit/issues/736

            if not isinstance(kde_copy, _KDEPDF):
                raise ValueError(f'Copy of KDE is not a {_KDEPDF}')

            return kde_copy

        fractions = [ 
            fraction for model, fraction in zip(self.models, self.fractions, strict = True) 
            if model.pdf is not None ]

        arrays : dict[str,numpy.ndarray] = dict()
        for attr_name in _MODEL_ATTRS:
            arrays[attr_name] = getattr(self, attr_name) 

        norm_fractions = [ fraction / sum(fractions) for fraction in fractions ]
        
        log.debug('Adding PDFs')
        pdf  = zfit.pdf.SumPDF(
            obs  = self.obs,
            norm = self.obs,
            pdfs = pdfs, 
            fracs= norm_fractions)

        for name, array in arrays.items():
            setattr(pdf, name, array)

        return pdf
    # -------------------------
    @cached_property
    def sam(self) -> numpy.ndarray:
        arrays = [ model.sam for model in self.models ]

        return numpy.concatenate(arrays)
    # -------------------------
    @cached_property
    def dec(self) -> numpy.ndarray:
        arrays = [ model.dec for model in self.models ]

        return numpy.concatenate(arrays)
    # -------------------------
    @cached_property
    def wgt(self) -> numpy.ndarray:
        arrays = [ model.wgt for model in self.models ]

        return numpy.concatenate(arrays)
    # -------------------------
    @cached_property
    def mass(self) -> numpy.ndarray:
        arrays = [ model.mass for model in self.models ]

        return numpy.concatenate(arrays)
#-----------------------------------------------------------
class PRec(Cache):
    '''
    Class used to calculate the PDF associated to the partially reconstructed background
    '''
    #-----------------------------------------------------------
    def __init__(
        self,
        name  : str,
        cfg   : CCbarConf,
        obs   : zobs,
        trig  : Trigger,
        q2bin : Qsq):
        '''
        Parameters:
        -------------------------
        name  : Fit category name
        cfg   : Configuration needed to build PDF
        obs   : Observable
        trig  : HLT2 trigger.
        q2bin : q2 bin
        '''
        self._obs      = obs
        self._name     = name
        self._cfg      = cfg
        self._trig     = trig
        self._q2bin    = q2bin
        self._d_fstat  = {}
        self._cut_info : dict[str, tuple[RDF.RCutFlowReport, dict[Cuts,str]]] = {}
        d_rdf, uid     = self.__get_samples_rdf()
        self._d_rdf    = d_rdf

        self._d_match  = self.__get_match_str()

        # This should be usable to make hashes
        # backlashes and dollar signs are not hashable in strings
        d_hash_match = { slugify.slugify(ltex) : value for ltex, value in self._d_match.items() }

        super().__init__(
            out_path = Path(Component.ccbar) / 'fit' / name,
            uid      = uid,
            conf     = cfg.model_dump(),
            d_match  = d_hash_match)
    #-----------------------------------------------------------
    def __get_df(self) -> dict[str,pnd.DataFrame]:
        r'''
        Returns
        -------------------
        Dictionary where:

        Key  : Identifier for ccbar component, e.g. "$B_d\to c\bar{c}(\to ee)H_s$"
        Value: Dictionary with:
            Key  : Name of component
            Value: Dataframe with entries for only that component
        '''
        d_df = self.__get_samples_df()
        d_df = { sample : self.__add_dec_weights(sample, df) for sample, df in d_df.items() }
        df   = pnd.concat(d_df.values(), axis=0)
        df   = self.__add_sam_weights(df)

        arr_wgt      = df.wgt_dec.to_numpy().astype(float) * df.wgt_sam.to_numpy().astype(float)
        df['wgt_br'] = self.__normalize_weights(arr_wgt)

        d_df = { component : df.query(cut) for component, cut in self._d_match.items() }

        return d_df
    #-----------------------------------------------------------
    def __need_var(self, name : str) -> bool:
        needed = False

        if name.endswith('ID'):
            needed = True

        if name in _MASSES:
            needed = True

        if needed:
            log.debug(f'Picking up column: {name}')

        return needed
    #-----------------------------------------------------------
    def __filter_rdf(
        self,
        rdf       : RDF.RNode,
        uid       : str,
        component : Component) -> tuple[RDF.RNode,str]:
        '''
        Parameters
        -----------------
        rdf       : ROOT dataframe before selection
        uid       : Unique identifier of dataframe
        component : Fit component for which selection is needed 

        Returns
        -----------------
        Tuple with:

        - ROOT dataframe after selection
        - Updated Unique identifier that takes into account the selection
        '''
        d_sel      = sel.selection(
            trigger=self._trig, 
            q2bin  =self._q2bin, 
            process=component)

        d_sel[Cuts.mass] = '(1)'
        for name, expr in d_sel.items():
            rdf = rdf.Filter(expr, name)

        rep = rdf.Report()

        self._cut_info[component] = rep, d_sel

        uid = hashing.hash_object([uid, d_sel])

        return rdf, uid
    # ----------------------
    def __save_cutflow(
        self, 
        report    : RDF.RCutFlowReport, 
        sample    : str,
        selection : dict[Cuts,str]) -> None:
        '''
        Parameters
        -------------
        report   : Cutflow report
        sample   : Sample to which selection was applied
        selection: Dictionary with key the cut identifier and value the actual cut
        '''
        df = rut.rdf_report_to_df(rep=report)

        log.info(f'Saving cutflow to: {self._out_path}')

        df.to_markdown(self._out_path / f'{sample}.md')
        gut.dump_json(data=selection, path= self._out_path / f'{sample}.yaml', exists_ok=True)
    #-----------------------------------------------------------
    def __get_samples_rdf(self) -> tuple[dict[CCbarComponent,RDF.RNode],str]:
        '''
        IMPORTANT: This method has to run dataframe creation lazily

        Returns
        -----------------
        Tuple of 2 elements:

        - Dictionary with
            - Key: Name of the ccbar sample
            - Value: ROOT dataframe after the selection

        - Concatenation of unique identifiers
        '''
        d_rdf : dict[CCbarComponent, RDF.RNode] = {}
        full_uid = ''
        for component in self._cfg.samples:
            gtr        = RDFGetter(sample=component, trigger=self._trig)
            rdf        = gtr.get_rdf(per_file=False)
            uid        = gtr.get_uid()
            rdf, uid   = self.__filter_rdf(rdf=rdf, component=component, uid=uid)

            d_rdf[component] = rdf
            full_uid     += uid

        return d_rdf, full_uid
    #-----------------------------------------------------------
    def __get_samples_df(self) -> dict[str,pnd.DataFrame]:
        '''
        Returns
        ------------------
        Dictionary with:

        - Key: Name of ccbar sample
        - Value: Pandas dataframe with only the needed columns
        '''
        d_df : dict[str, pnd.DataFrame] = {}
        log.debug('Building pandas dataframes:')
        for sample, rdf in self._d_rdf.items():
            log.debug(f'    {sample}')

            if log.getEffectiveLevel() < LogLevels.info:
                rep = rdf.Report()
                rep.Print()

            l_var      = [ name.c_str() for name in rdf.GetColumnNames() if self.__need_var( name.c_str() )]
            data       = rdf.AsNumpy(l_var)
            df         = pnd.DataFrame(data)
            df['proc'] = sample

            d_df[sample] = df

        return d_df
    #-----------------------------------------------------------
    def __add_dec_weights(
        self, 
        sample : str, 
        df     : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        sample: Name of ccbar sample
        df    : DataFrame with masses

        Returns
        --------------
        DataFrame with dec(ay) weights added
        '''
        dec = self._cfg.weights[CCbarWeight.dec]

        if  dec:
            log.debug(f'Adding decay weights to: {sample}')
            val : pnd.Series = df.apply(read_weight, args=(self._trig.project,), axis=1)
            df['wgt_dec']    = 1. if val.empty else val
        else:
            log.warning(f'Not using decay weights in: {sample}')
            df['wgt_dec']    = 1.

        arr_wgt      = df.wgt_dec.to_numpy()
        arr_wgt      = self.__normalize_weights(arr_wgt)
        df['wgt_dec']= arr_wgt

        return df
    #-----------------------------------------------------------
    def __add_sam_weights(
        self, 
        df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        --------------
        df    : DataFrame with masses

        Returns
        --------------
        DataFrame with sam(ple) weights added
        '''

        sam = self._cfg.weights[CCbarWeight.sam]

        if   sam:
            log.debug('Adding sample weights')
            obj              = SampleWeightReader(df = df)
            val : pnd.Series = obj.get_weights()
            df['wgt_sam']    = 1. if val.empty else val
        else:
            log.warning('Not using sample weights')
            df['wgt_sam']    = 1.

        arr_wgt      = df.wgt_sam.to_numpy()
        arr_wgt      = self.__normalize_weights(arr_wgt)
        df['wgt_sam']= arr_wgt

        return df
    #-----------------------------------------------------------
    def __get_match_str(self) -> dict[str,str]:
        '''
        Returns
        ----------------
        _selection_ needed to split the charmonium sample into components
        for plotting
        '''
        if   self._q2bin == Qsq.jpsi:
            d_match = self.__get_match_str_jpsi()
        elif self._q2bin == Qsq.psi2:
            d_match = self.__get_match_str_psi2()
        elif self._q2bin in [Qsq.low, Qsq.central, Qsq.high]:
            d_match = self.__get_match_str_psi2()
        else:
            raise ValueError(f'Invalid q2bin: {self._q2bin}')

        return d_match
    #-----------------------------------------------------------
    def __get_match_str_jpsi(self) -> dict[str,str]:
        '''
        The Jpsi splitting splits by B kind, i.e. three components, Bd, Bu, Bs 

        Returns
        ------------
        Dictionary mapping 

        - Latex string describing process
        - Truth matching string isolating process
        '''
        bs = '(abs(B_TRUEID) == 531)'
        bd = '(abs(B_TRUEID) == 511)'
        bp = '(abs(B_TRUEID) == 521)'

        d_cut : dict[str,str] = {}
        if self._trig.is_electron:
            d_cut[r'$B_s\to c\bar{c}(\to e^+ e^-)H_s$'] = bs
            d_cut[r'$B_d\to c\bar{c}(\to e^+ e^-)H_s$'] = bd
            d_cut[r'$B^+\to c\bar{c}(\to e^+ e^-)H_s$'] = bp
        elif self._trig.is_muon:
            d_cut[r'$B_s\to c\bar{c}(\to \mu^+\mu^-)H_s$'] = bs
            d_cut[r'$B_d\to c\bar{c}(\to \mu^+\mu^-)H_s$'] = bd
            d_cut[r'$B^+\to c\bar{c}(\to \mu^+\mu^-)H_s$'] = bp
        else:
            raise ValueError(f'Invalid trigger: {self._trig}')

        return d_cut
    #-----------------------------------------------------------
    def __get_match_str_psi2(self) -> dict[str,str]:
        '''
        The psi2S splitting splits by B meson type, BUT for Bu, it separates the component with a psi2S -> Jpsi

        Returns
        ------------
        Dictionary mapping 

        - Latex string describing process
        - Truth matching string isolating process
        '''
        bd = '(abs(B_TRUEID) == 511)'
        bp = '(abs(B_TRUEID) == 521)'
        bs = '(abs(B_TRUEID) == 531)'

        psjp     = '(abs(Jpsi_TRUEID) == 443) & (abs(Jpsi_MC_MOTHER_ID) == 100443) & (abs(Jpsi_MC_GD_MOTHER_ID) == 521)' 
        bp_psjp  = f'{bp} & {psjp}'

        neg_psjp = psjp.replace('==', '!=').replace('&' , '|')
        bp_ex    = f'{bp} & ({neg_psjp})'

        d_cut : dict[str,str] = {}
        d_cut[r'$B^+\to \psi(2S)(\to J/\psi+X)H_{s}$'] = bp_psjp 
        if   self._trig.is_electron: 
            d_cut[r'$B^+\to c\bar{c}(\to e^+ e^-)H_s$']    = bp_ex
            d_cut[r'$B_d\to c\bar{c}(\to e^+ e^-)H_s$']    = bd
            d_cut[r'$B_s\to c\bar{c}(\to e^+ e^-)H_s$']    = bs
        elif self._trig.is_muon: 
            d_cut[r'$B^+\to c\bar{c}(\to \mu^+\mu^-)H_s$'] = bp_ex
            d_cut[r'$B_d\to c\bar{c}(\to \mu^+\mu^-)H_s$'] = bd
            d_cut[r'$B_s\to c\bar{c}(\to \mu^+\mu^-)H_s$'] = bs
        else:
            raise ValueError(f'Trigger not associated to electron or muon channel: {self._trig}')

        return d_cut
    #-----------------------------------------------------------
    def __normalize_weights(self, arr_wgt : numpy.ndarray) -> numpy.ndarray:
        tot_wgt : float = arr_wgt.sum()
        num_wgt : int   = arr_wgt.shape[0]
        fact            = num_wgt / tot_wgt
        arr_wgt         = fact * arr_wgt

        return arr_wgt
    #-----------------------------------------------------------
    def __model_from_df(
        self, 
        name : str,
        mass : Mass,
        cfg  : KDEConf,
        df   : pnd.DataFrame) -> CharmoniumComponent:
        '''
        Parameters
        --------------
        name: Component name, e.g. bpjpsix
        mass: Used to read column in dataframe and extract data to be fitted
        cfg : KDE configuration
        df  : DataFrame with data to be fitted

        Returns
        --------------
        Object holding data to fit with weights
        '''
        try:
            arr_mass = df[mass     ].to_numpy()
            arr_wgt  = df['wgt_br' ].to_numpy()
            arr_sam  = df['wgt_sam'].to_numpy()
            arr_dec  = df['wgt_dec'].to_numpy()
        except Exception as exc:
            for column in df.columns:
                log.error(column)

            log.info(f'Trigger: {self._trig}')
            log.info(f'Q2bin  : {self._q2bin}')
            log.info(f'Samples: {self._cfg.samples}')

            raise ValueError(f'Cannot access {mass} and wgt_br') from exc

        model = CharmoniumComponent(
            name= name,
            obs = self._obs,
            cfg = cfg,
            mass= arr_mass, 
            wgt = arr_wgt, 
            sam = arr_sam, 
            dec = arr_dec)

        return model
    #-----------------------------------------------------------
    def __get_model(
        self,
        mass           : Mass,
        df             : pnd.DataFrame,
        component_name : str,
        q2bin          : Qsq) -> CharmoniumComponent:
        '''
        Parameters
        ------------------
        name    : Latex name of PDF component
        mass    : Mass to be fitted
        df      : DataCorresponding to given ccbar component
        q2bin   : q2bin for which mdoel is needed 

        Returns
        ------------------
        Model object, holding PDF (or None) and arrays used to build it
        '''
        cfg      = self._cfg.fit[q2bin]

        model    = self.__model_from_df(
            name = component_name,
            df   = df, 
            cfg  = cfg,
            mass = mass)

        plot_name = slugify.slugify(text=component_name, lowercase=False)

        self._plot_weights(
            model   = model, 
            name    = plot_name, 
            title   = component_name, 
            out_dir = self._out_path)

        self._plot_pdf(
            model  = model, 
            title  = component_name,
            name   = plot_name,
            out_dir= self._out_path)

        return model 
    #-----------------------------------------------------------
    #-----------------------------------------------------------
    def __yield_in_range(self, model : CharmoniumComponent) -> float:
        '''
        The mass and weights are defined in the WHOLE range. This method extracts the yields
        in the observable range. Needed to calculate fractions of componets, used to put
        ccbar stuff together

        Parameters
        ---------------
        model: Holding PDF and arrays used to build it 

        Returns
        ---------------
        Weighted yield of dataset used to build PDF in range where PDF is defined
        '''
        if model.pdf is None:
            raise ValueError('PDF associated to model should not be None, but it is')

        arr_mass   = model.mass
        arr_weight = model.wgt
        obs        = model.pdf.space

        return self.__yield_from_arrays(masses = arr_mass, weights = arr_weight, obs = obs)
    #-----------------------------------------------------------
    def __yield_from_arrays(
        self, 
        masses  : numpy.ndarray, 
        weights : numpy.ndarray, 
        obs     : zobs) -> float:
        '''
        Returns
        -----------------
        Yeld in observable from sum of weights
        '''
        minx, maxx = sut.range_from_obs(obs=obs)
        mask       = (minx < masses) & (masses < maxx)
        wgt        = weights[mask]

        return sum(wgt)
    #-----------------------------------------------------------
    def __get_full_model(self, d_df : dict[str,pnd.DataFrame]) -> CCbarModel: 
        '''
        Parameters
        -------------------
        d_df  : Dictionary with:
            Key  : Latex name of component, not necessarily Bu/Bd... This was re-split
            Value: Dataframe with data to fit

        Returns
        -------------------
        Full pdf, i.e. all ccbar components added
        '''
        if not d_df:
            raise ValueError('No dataframes with components data')

        if self._cfg.merged[self._q2bin]:
            return self.__get_full_merged_model(d_df = d_df)
        else:
            return self.__get_full_split_model(d_df = d_df)
    #-----------------------------------------------------------
    def __get_full_merged_model(self, d_df : dict[str,pnd.DataFrame]) -> CCbarModel:
        dfs   = [ df for df in d_df.values() ]
        df    = pnd.concat(objs = dfs, axis = 0)
        model = self.__get_model(
            mass           = Mass(self._obs.label), 
            component_name = _MERGED_PDFNAME, 
            df             = df, 
            q2bin          = self._q2bin)

        merged_model = CCbarModel(
            name      = f'{_MERGED_PDFNAME}_{self._name}',
            obs       = self._obs,
            models    = [model], 
            fractions = [1])

        return merged_model
    #-----------------------------------------------------------
    def __get_full_split_model(
        self, 
        d_df : dict[str,pnd.DataFrame]) -> CCbarModel:
        all_models: list[CharmoniumComponent] = [ 
            self.__get_model(
                mass           = Mass(self._obs.label), 
                component_name = ltex, 
                df             = df, 
                q2bin          = self._q2bin) for ltex, df in d_df.items() ]

        models    : list[CharmoniumComponent] = [ model for model in all_models if model.pdf is not None ]
        yields    : list[float   ] = [ self.__yield_in_range(model=model) for    model in models ]
        fractions : list[float   ] = [ wgt_yld / sum(yields)              for  wgt_yld in yields ]

        model = CCbarModel(
            name      = f'{_MERGED_PDFNAME}_{self._name}',
            obs       = self._obs,
            models    = models, 
            fractions = fractions)

        return model
    #-----------------------------------------------------------
    def _plot_pdf(
        self,
        model   : CharmoniumComponent | CCbarModel,
        name    : str,
        out_dir : Path,
        title   : str          = '',
        maxy    : float | None = None) -> None:
        '''
        Utility method, meant to plot PDF after it was built

        Parameters
        ------------------
        model  : Object storing PDF
        neme   : used to name the PNG file as {name}.png
        title  : Title for plots, will be appended after number of entries
        maxy   : Will be used to plot fit properly in case labels overlap
        out_dir: Directory where plots will go
        '''
        if isinstance(model, CCbarModel) and model.is_empty:
            return

        if model.pdf:
            obj = ZFitPlotter(
                data   = model.mass, 
                model  = model.pdf, 
                weights= model.wgt)
            obj.run(cfg = self._cfg.plots)

            obj.axs[0].set_title(f'#Entries: {model.mass.size}; {title}')

            if maxy is not None:
                obj.axs[0].set_ylim(bottom=0, top=maxy)

            obj.axs[0].axvline(x=5080, linestyle=':')
            obj.axs[0].axvline(x=5680, linestyle=':')
            obj.axs[0].axvline(x=5280, label=r'$B^+$', color='gray', linestyle='--')

            obj.axs[1].set_ylim(-5, +5)
            obj.axs[1].axhline(y=-3, color='red')
            obj.axs[1].axhline(y=+3, color='red')
            obj.axs[1].set_label('M$(B^+)$[MeV/${}_{c^2}$]')
        else:
            log.warning(f'PDF {name} not built')
            nentries = len(model.mass)

            plt.figure(figsize=(15,10))
            plt.title(f'Entries = {nentries}; {title}')
            plt.hist(model.mass, weights=model.wgt, bins=100)

        out_dir.mkdir(parents = True, exist_ok = True)

        plot_path = out_dir / f'{name}.png'
        log.info(f'Saving to: {plot_path}')
        plt.savefig(plot_path)
        plt.close('all')
    #-----------------------------------------------------------
    def _plot_weights(
        self, 
        model   : CCbarModel | CharmoniumComponent,
        name    : str,
        title   : str,
        out_dir : Path) -> None:
        '''
        Save plot of weights and PDF as text

        Parameters
        -------------------
        model  : Object holding PDF and data used to make it
        name   : Name of plot and place where PDF will be saved as text, i.e. {name}.png, {name}.txt
        title  : Plot title
        out_dir: Directory where files will be saved
        '''
        if isinstance(model, CCbarModel) and model.is_empty:
            return

        plt.hist(model.sam, bins=30, label='sample', histtype='step', linestyle='-' )
        plt.hist(model.dec, bins=30, label='decay' , histtype='step', linestyle='--')
        plt.hist(model.wgt, bins=30, label='Total' , histtype='step', linestyle=':' )

        plt.legend()
        plt.title(title)
        plt.savefig(out_dir / f'{name}_wgt.png')
        plt.close('all')

        if model.pdf is None:
            return

        text_path = f'{out_dir}/{name}.txt' 
        sut.print_pdf(model.pdf, txt_path=text_path)
    #-----------------------------------------------------------
    def get_sum(self, name : str) -> zfit.pdf.SumPDF | _KDEPDF | None:
        '''
        Provides extended PDF that is the sum of multiple KDEs representing PRec background

        Parameters
        ----------------
        name  : Name of PDF, used for title and PNG name

        Returns:
        ----------------
        Sum of all charmonium components or None if no PDF could be made
        '''
        l_ltex      = list(self._d_match) # Get component names in latex and map them to parquet files to save
        d_ltex_slug = { ltex : slugify.slugify(ltex, lowercase=False) for ltex       in l_ltex }
        d_path      = { ltex : self._out_path / f'{slug}.parquet'     for ltex, slug in d_ltex_slug.items() }

        plot_name   = slugify.slugify(name, lowercase=False)
        if self._copy_from_cache():
            log.info(f'Data found cached, reloading from {self._out_path}')
            d_df = { ltex : pnd.read_parquet(path) for ltex , path in d_path.items() }
            model= self.__get_full_model(d_df=d_df)

            self._plot_weights(
                model   = model, 
                name    = plot_name, 
                title   = name, 
                out_dir = self._out_path)

            self._plot_pdf(
                model  =model,
                title  =name,
                name   =plot_name,
                out_dir=self._out_path)

            return model.pdf

        log.info(f'Recalculating, cached data not found in: {self._out_path}')

        d_df = self.__get_df()
        model= self.__get_full_model(d_df = d_df)

        for sample in self._cut_info:
            rep, d_sel = self._cut_info[sample]
            self.__save_cutflow(report=rep, sample=sample, selection=d_sel)

        # Save dataframes before caching
        # Cache at the very end
        log.info('Saving dataframes:')
        for ltex, df in d_df.items():
            path = d_path[ltex]
            log.info(f'   {path}')
            df.to_parquet(path)

        self._plot_weights(
            model   = model, 
            name    = plot_name, 
            title   = name, 
            out_dir = self._out_path)

        self._plot_pdf(
            model   = model,
            title   = name,
            name    = plot_name,
            out_dir = self._out_path)

        self._cache()

        return model.pdf
#-----------------------------------------------------------
