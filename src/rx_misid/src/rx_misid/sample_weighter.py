'''
Module with SampleWeighter class
'''
import os
import re
import glob
import math
import pickle

import numpy
import pandas as pnd

from dmu                import LogStore
from numpy              import typing       as numpy_typing
from boost_histogram    import Histogram    as bh
from boost_histogram    import accumulators as acc
from .types             import MisIDSampleWeights

log=LogStore.add_logger('rx_misid:sample_weighter')

BREM       ='brem'
NOBREM     ='nobrem'
FloatArray = numpy_typing.NDArray[numpy.float64]
# ------------------------------
class SampleWeighter:
    '''
    Class intended to:

    - Read calibration maps
    - Pick datasets
    - Apply weights to datasets and return them
    '''
    _regex  = r'.*_(block\d)(?:_v\d)?-(?:up|down)-(K|Pi)-.*'
    # ------------------------------
    def __init__(
        self,
        df     : pnd.DataFrame,
        is_sig : bool,
        sample : str,
        cfg    : MisIDSampleWeights):
        '''
        Parameters
        -----------------
        df    : Pandas dataframe with columns including 'hadron' and 'kind'. Used to assign weights
        is_sig: If true, the weights will provide signal region sample, otherwise control region
        sample: E.g. DATA_24_... Needed to pick maps based on actual particle identity
        cfg   : omegaconf dictionary storing configuration
        '''
        self._cfg    = cfg
        self._is_sig = is_sig
        self._sample = sample
        self._varx   : str
        self._vary   : str
        self._l_kind = [BREM, NOBREM]

        #PT:
        #    True : 10
        #    False: 20
        self._d_out_of_map : dict[str,dict[bool,int]] = {}
        self._d_quality    : dict[str,int] = {
            'NaN'      : 0,
            'Inf'      : 0,
            'Negative' : 0,
            'Zeroes'   : 0,
            'Good'     : 0,
            'Ones'     : 0,
            'Above 1'  : 0}

        self._set_variables()
        self._df                              = self._get_df(df)
        self._d_map : dict[str, dict[str,bh]] = { kind : self.get_maps(cfg = cfg, kind = kind) for kind in self._l_kind }
    # ------------------------------
    def _get_df(self, df : pnd.DataFrame) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        df : Pandas dataframe with input

        Returns
        ---------------
        Input dataframe with columns added.
        '''

        df = self._add_columns(df=df, particle='L1')
        df = self._add_columns(df=df, particle='L2')

        return df
    # ------------------------------
    def _add_columns(self, df : pnd.DataFrame, particle : str) -> pnd.DataFrame:
        '''
        Parameters
        ---------------
        df      : Pandas dataframe with input
        particle: Name of particle for which columns are needed, e.g. L1

        Returns
        ---------------
        Dataframe with columns for X and Y axes added. These axes are the ones
        in function of which PIDCalib maps are parametrized
        '''
        for template in [self._varx, self._vary]:
            var = template.replace('PARTICLE', particle)
            if var in df.columns:
                log.debug(f'Variable {var} already found, not adding it')
                continue

            log.info(f'Adding column: {var}')
            df[var] = df.eval(var)

        return df
    # ------------------------------
    @staticmethod
    def _key_from_path(path : str, cfg : MisIDSampleWeights) -> str:
        '''
        Parameters
        ---------------
        path: Path to pickle file holding the calibration map
        cfg : Configuration used for weights, usually called weights.yaml

        Returns
        ---------------
        Identifier, needed as key of dictionary holding maps
        '''
        file_name = os.path.basename(path)
        mtch = re.match(SampleWeighter._regex, file_name)
        if not mtch:
            raise ValueError(f'Cannot find block and particle in: {file_name}')

        [block, part] = mtch.groups()

        part = {'K': 'kaon', 'Pi' : 'pion'}[part]

        if   cfg.regions['signal']  in file_name:
            region = 'signal'
        elif cfg.regions['control'] in file_name:
            region = 'control'
        else:
            raise ValueError(f'Cannot determine region from: {file_name}')

        return f'{block}_{part}_{region}'
    # ------------------------------
    @staticmethod
    def get_maps(
        cfg  : MisIDSampleWeights,
        kind : str) -> dict[str, bh]:
        '''
        Loads pickle files with PIDCalib2 efficiencies for
        kaons or pions and returns them

        Parameters
        ----------------
        kind     : Describes things like brem or no brem or different binnings
        cfg      : Configuration meant to control weights
        maps_path: Path containing `brem`, `nobrem` directories, inside ANADIR

        Returns
        ----------------
        Dictionary mapping string identfying maps and
        boosthistogram object
        '''
        log.info(f'Reading maps from: {cfg.maps_path}')

        ana_dir = os.environ['ANADIR']
        pkl_dir = f'{ana_dir}/{cfg.maps_path}/{kind}'
        path_wc = f'{pkl_dir}/*.pkl'
        l_path  = glob.glob(path_wc)

        d_map = {}
        for path in sorted(l_path):
            log.verbose(f'Reading: {path}')

            key = SampleWeighter._key_from_path(path=path, cfg = cfg)
            with open(path, 'rb') as ifile:
                try:
                    hist = pickle.load(ifile)
                except EOFError as exc:
                    raise EOFError(f'Cannot open map: {path}') from exc

            d_map[key] = hist

        return d_map
    # ------------------------------
    def _set_variables(self) -> None:
        l_var = self._cfg.pars
        if len(l_var) != 2:
            raise NotImplementedError(f'Only 2D reweighing suppored, requested: {l_var}')

        self._varx = l_var[0]
        self._vary = l_var[1]
    # ------------------------------
    def _get_bin_index(
        self,
        hist  : bh,
        iaxis : int,
        value : float,
        name  : str) -> int:
        '''
        Parameters
        ------------------
        hist : Boost histogram
        iaxis: Axis index, 0 or 1
        value: Value of variable whose intex is read for `iaxis`
        name : Name of the variable corresponding to `iaxis`

        Returns
        ------------------
        Index of bin in map for given `value` in given histogram
        '''
        axis = hist.axes[iaxis]
        minv = axis.edges[ 0] * 1.001
        maxv = axis.edges[-1] * 0.999

        old_value = value
        new_value = max(old_value, minv)
        new_value = min(new_value, maxv)

        if old_value != new_value:
            is_max = old_value > maxv
            if name not in self._d_out_of_map:
                self._d_out_of_map[name] = {True : 0, False : 0}

            self._d_out_of_map[name][is_max] += 1

        index = axis.index(new_value)

        return index
    # ------------------------------
    def _get_lepton_eff(
        self,
        row    : pnd.Series,
        lep    : str,
        is_sig : bool) -> float:
        '''
        Reads loaded PID efficiency maps and returns efficiency, for a given particle
        This method assumes that the particles is not a true electron, but a hadron

        Parameters
        ----------------
        lep   : L1 or L2
        row   : Contains candidate information
        is_sig: Used to pick correct efficiency map

        Returns
        ----------------
        Lepton PID efficiency
        '''
        block   = int(row.block)
        key_map = f'block{block}_{row.hadron}_signal' if is_sig else f'block{block}_{row.hadron}_control'
        brem_key= self._get_brem_key(lep=lep, row=row)
        try:
            hist    = self._d_map[brem_key][key_map]
        except KeyError as exc:
            for key, d_map in sorted(self._d_map.items()):
                log.info(key)
                for val in sorted(d_map):
                    log.info(f'   {val}')

            raise KeyError(f'Cannot pick up PID map: {key_map}') from exc

        varx = self._varx.replace('PARTICLE', lep)
        vary = self._vary.replace('PARTICLE', lep)

        x_value = getattr(row, varx)
        y_value = getattr(row, vary)

        ix = self._get_bin_index(hist, iaxis=0, value=x_value, name=varx)
        iy = self._get_bin_index(hist, iaxis=1, value=y_value, name=vary)
        eff= hist[ix, iy]

        if isinstance(eff, acc.WeightedSum):
            eff = eff.value

        if not isinstance(eff, float):
            etype = type(eff)
            raise NotImplementedError(f'Unrecognized efficiency of type: {etype}')

        eff = self._check_eff(eff=eff, x=x_value, y=y_value)

        return eff
    # ----------------------
    def _get_brem_key(self, lep : str, row : pnd.Series) -> str:
        '''
        Parameters
        -------------
        lep: Name of lepton in this iteration, e.g. L1
        row: Row containing information of candidate

        Returns
        -------------
        Identifier for brem category, e.g brem, nobrem
        '''
        name  = f'{lep}_HASBREM'
        value = row[name]

        if value == 1:
            return BREM

        if value == 0:
            return NOBREM

        raise ValueError(f'Invalid {name} value: {value}')
    # ------------------------------
    def _check_eff(self, eff : float, x : float, y : float) -> float:
        '''
        Parameters
        ---------------
        eff: Efficiency
        x/y: Coordinates in map associated to efficiency

        Returns
        ---------------
        efficiency after sanitation step
        '''
        if 0 <= eff <= 1:
            if   math.isclose(eff, 0, rel_tol=1e-5):
                self._d_quality['Zeroes'] += 1
            elif math.isclose(eff, 1, rel_tol=1e-5):
                self._d_quality['Ones'] += 1
            else:
                self._d_quality['Good'] += 1

            return eff

        log.verbose('')

        if math.isinf(eff):
            log.verbose('At:')
            log.verbose(f'X={x:.2f}')
            log.verbose(f'Y={y:.2f}')
            log.verbose(f'Eff={eff:0.3} returning 0')
            self._d_quality['Inf'] += 1

            return 0.0

        if math.isnan(eff):
            log.verbose('At:')
            log.verbose(f'X={x:.2f}')
            log.verbose(f'Y={y:.2f}')
            log.verbose(f'Eff={eff:0.3} returning 0')
            self._d_quality['NaN'] += 1

            return 0.0

        log.verbose('At:')
        log.verbose(f'X={x:.2f}')
        log.verbose(f'Y={y:.2f}')
        log.verbose(f'Eff={eff:0.3}')

        if eff < 0:
            self._d_quality['Negative'] += 1
            return 0.0

        if eff > 1:
            self._d_quality['Above 1'] += 1
            return 1.0

        raise ValueError(f'Unexpected efficiency value: {eff}')
    # ------------------------------
    def _print_info_from_row(self, row : pnd.Series) -> None:
        '''
        Prints coordinates at current point

        Parameters
        -----------------
        row: Pandas series representing entry in tree
        '''
        log.verbose(40 * '-')
        log.verbose(f'Block/Hadron: {row.block}/{row.hadron}')
        log.verbose(40 * '-')
        for lepton in ['L1', 'L2']:
            varx = self._varx.replace('PARTICLE', lepton)
            vary = self._vary.replace('PARTICLE', lepton)

            valx = getattr(row, varx)
            valy = getattr(row, vary)

            log.verbose(f'{varx:<20}{valx:20.2f}')
            log.verbose(f'{vary:<20}{valy:20.2f}')
            log.verbose('')
    # ------------------------------
    def _print_stats(self, wgt : numpy.ndarray) -> None:
        '''
        This method will print a summary of the number of entries that
        ended up outside the maps, too high or too low

        Parameters
        ----------------
        wgt: Array of weights
        '''
        log.info(40 * '-')
        log.info(f'{"Value":<20}{"Frequency":<20}')
        log.info(40 * '-')
        for kind, val in self._d_quality.items():
            log.info(f'{kind:<20}{val:<20}')
        log.info(40 * '-')
        log.info('')
        log.info(f'Processed {len(self._df)} entries')
        log.info(40 * '-')
        log.info(f'{"Variable":<20}{"Low":<10}{"High":<10}')
        log.info(40 * '-')
        for var, d_frq in self._d_out_of_map.items():
            val_low  = d_frq.get(False,0)
            val_high = d_frq.get(True ,0)
            log.info(f'{var:<20}{val_low:<10}{val_high:<10}')
        log.info(40 * '-')
        log.info('')
        nwgt = len(wgt)
        sumw = numpy.sum(wgt)

        log.info(f'{"Entries":<20}{nwgt:<20}'   )
        log.info(f'{"SumW   ":<20}{sumw:<20.2f}')
    # ----------------------
    def _get_arrays(self, has_brem : bool) -> tuple[FloatArray, FloatArray, FloatArray]:
        '''
        Parameters
        -------------
        has_brem: True to pick up only tracks with brem

        Returns
        -------------
        Tuple with arrays with log(PT), ETA and Weights for tracks with(out)
        brem depending on `has_brem`. These arrays should contain both leptons
        '''
        brem_val   = 1 if has_brem else 0
        df_l1      = self._df[self._df['L1_HASBREM'] == brem_val]
        df_l2      = self._df[self._df['L2_HASBREM'] == brem_val]

        arr_l1_pt  = df_l1['L1_TRACK_PT' ].to_numpy()
        arr_l2_pt  = df_l2['L2_TRACK_PT' ].to_numpy()

        arr_l1_eta = df_l1['L1_TRACK_ETA'].to_numpy()
        arr_l2_eta = df_l2['L2_TRACK_ETA'].to_numpy()

        arr_l1_wgt = df_l1['weight'].to_numpy()
        arr_l2_wgt = df_l2['weight'].to_numpy()

        arr_pt = numpy.concatenate((arr_l1_pt , arr_l2_pt ))
        arr_eta= numpy.concatenate((arr_l1_eta, arr_l2_eta))
        arr_wgt= numpy.concatenate((arr_l1_wgt, arr_l2_wgt))
        arr_pt = numpy.log10(arr_pt)

        return arr_pt, arr_eta, arr_wgt
    # ----------------------
    def get_weighted_data(self) -> pnd.DataFrame:
        '''
        Returns
        --------------------
        Input dataframe with:

        - Variables to read X and Y axis defined
        - Updated `weight` column with PID weights, e.g. product of efficiencies for each track
        - Attached `pid_weights` column
        '''
        if len(self._df) == 0:
            log.warning('Empty dataframe, not assigning any weight')
            return self._df

        log.info(f'Getting signal={self._is_sig} PID weights for sample {self._sample}')

        try:
            sr_eff_l1 = self._df.apply(self._get_lepton_eff, args=('L1', self._is_sig), axis=1)
            sr_eff_l2 = self._df.apply(self._get_lepton_eff, args=('L2', self._is_sig), axis=1)

            arr_eff_l1 = sr_eff_l1.to_numpy()
            arr_eff_l2 = sr_eff_l2.to_numpy()
            arr_wgt    = arr_eff_l1 * arr_eff_l2
        except AttributeError as exc:
            log.warning('Found columns:')
            for column in self._df.columns:
                log.info(f'    {column}')
            raise AttributeError('Cannot assign weight') from exc

        self._print_stats(wgt=arr_wgt)

        self._df['weight']     *= arr_wgt
        self._df['pid_eff_l1']  = arr_eff_l1
        self._df['pid_eff_l2']  = arr_eff_l2
        self._df['pid_weights'] = arr_wgt

        return self._df
# ------------------------------
