'''
Module containing PhotonVeto class
'''
import re
import numpy
import pandas as pnd

from dmu         import LogStore
from typing      import Final
from pydantic    import BaseModel, ConfigDict, RootModel, model_validator
from dmu.generic import utilities as gut

REGEX : Final[str] = r'(0|1|2)_(\d+)-(\d+)_(\d+)'

log=LogStore.add_logger('rx_data:photon_veto')
# ------------------------------------
class EcalCell(BaseModel):
    '''
    Class meant to represent an ECAL cell
    '''
    model_config = ConfigDict(frozen=True)

    area : int
    row  : int
    col  : int
    # ------------------------------------
    def __str__(self):
        return f'{self.area:03d},{self.row:03d},{self.col:03d}'
    # ------------------------------------
    @classmethod
    def random(cls) -> 'EcalCell':
        '''
        Returns a random EcalCell, useful for tests
        '''
        area = numpy.random.choice([0, 1, 2])
        row  = numpy.random.randint(low = -60, high = 60)
        col  = numpy.random.randint(low =  14, high = 49)

        return cls(area = area, row = row, col = col)
    # ------------------------------------
    @classmethod
    def from_series(
        cls,
        series      : pnd.Series,
        lepton_name : str) -> 'EcalCell':
        '''
        Parameters
        ---------------
        lepton_name: E.g. L1 or L2
        series     : Pandas series with information on Lepton and its photon

        Return
        ---------------
        Cell in calorimeter
        '''
        data = series.to_dict()

        area = data[f'{lepton_name}_BREMHYPOAREA']
        row  = data[f'{lepton_name}_BREMHYPOROW' ]
        col  = data[f'{lepton_name}_BREMHYPOCOL' ]

        return cls(area = area, row = row, col = col)
# ------------------------------------
class EcalRegion(RootModel[list[EcalCell]]):
    '''
    Class meant to represent a collection of
    ECAL cells
    '''
    model_config = ConfigDict(frozen=True)
    # ----------------------
    @classmethod
    def _location_from_str(cls, string : str) -> set[tuple[int,int,int]]:
        '''
        Parameters
        ------------
        string: String representing locations of cells in ECAL

        Returns
        ------------
        Set of tuples with the area, row and column
        '''
        mtch = re.match(REGEX, string)
        if not mtch:
            raise ValueError(f'Cannot extract location from: {string}')

        area    = int(mtch.group(1))
        min_col = int(mtch.group(2))
        max_col = int(mtch.group(3))
        row     = int(mtch.group(4))

        if min_col >= max_col:
            raise ValueError(f'Column range is invalid: [{min_col},{max_col}]')

        cols = [ col for col in range(min_col, max_col + 1) ]

        return { (area, row, col) for col in cols }
    # ----------------------
    @model_validator(mode = 'before')
    @classmethod
    def preprocess(cls, data):
        '''
        Formats properly the input data
        '''
        new_data : list[dict[str,int]] = []
        for value in data:
            locations = cls._location_from_str(string = value)
            for area, row, col in locations:
                entry = {
                    'area' : area,
                    'row'  : row,
                    'col'  : col,
                }

                new_data.append(entry)

        return new_data
# ------------------------------------
class PhotonVeto:
    '''
    Class meant to veto photons based on
    location in calorimeter
    '''
    # ------------------------------------
    def __init__(self, version : str):
        '''
        Parameters
        ---------------
        version: Version of cells to veto, e.g. v1
        '''
        self._version   = version
        self._bad_cells = self._load_bad_cells()

        self._nvetoed = 0
        self._ntotal  = 0
    # ------------------------------------
    def _load_bad_cells(self) -> EcalRegion | None:
        data        = gut.load_data(
            package =  'rx_data_data',
            fpath   = f'calorimeter/veto/{self._version}.yaml')

        log.info(f'Loading cells from version {self._version} to veto')

        if data is None:
            log.warning(f'Not vetoing any calorimeter region for version: {self._version}')
            return None

        return EcalRegion(root = data)
    # ------------------------------------
    @property
    def nvetoed(self) -> int:
        return self._nvetoed
    # ------------------------------------
    @property
    def ntotal(self) -> int:
        return self._ntotal
    # ------------------------------------
    def veto(
        self,
        lepton_name : str,
        row         : pnd.Series) -> bool:
        '''
        Parameters
        ---------------
        lepton_name: E.g. L1 or L2
        row        : Pandas series with information on Lepton and its photon

        Return
        ---------------
        True if photon is meant to be picked, False otherwise
        '''
        self._ntotal += 1

        if self._bad_cells is None:
            return False

        cell = EcalCell.from_series(
            series      = row,
            lepton_name = lepton_name)

        return self.veto_cell(cell = cell)
    # ------------------------------------
    def veto_cell(self, cell : EcalCell) -> bool:
        '''
        Parameters
        ------------------
        cell: Instance of EcalCell

        Returns
        ------------------
        True if cell is meant to be vetoed
        '''
        if self._bad_cells is None:
            return False

        if cell in self._bad_cells.root:
            log.debug(f'Vetoing: {cell}')
            self._nvetoed += 1
            return True

        return False
# ------------------------------------
