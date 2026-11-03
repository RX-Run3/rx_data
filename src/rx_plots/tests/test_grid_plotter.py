'''
Module with tests for GridPlotter
'''
import numpy
import pandas as pnd

from functools  import cached_property
from gvar       import GVar, gvar
from pathlib    import Path
from pydantic   import BaseModel, ConfigDict, RootModel
from rx_plotter import GridPlotter

# -----------------------------------
class Loc(RootModel[list]):
    @property
    def location(self) -> tuple[float,...]:
        return 0.,
# -----------------------------------
class Node(BaseModel):
    @property
    def gauss(self) -> GVar:
        return gvar(0,0)

    @property
    def wp(self) -> Loc:
        return Loc(root = [])
# -----------------------------------
class Grid(RootModel[list[Node]]):
    model_config = ConfigDict(arbitrary_types_allowed = True)

    @cached_property
    def df(self) -> pnd.DataFrame:
        xax = numpy.linspace(0, 1, 10)
        yax = numpy.linspace(0, 1, 10)

        xval = []
        yval = []
        zval = []
        for x in xax:
            for y in yax:
                xval.append(x)
                yval.append(y)
                zval.append(x + y)

        df = pnd.DataFrame({'cmb' : xval, 'prc' : yval})
        df['yld'] = zval

        return df

    def at(self, wp : Loc, fall_back : Node | None) -> Node:
        _  = wp
        _  = fall_back
        return Node()
# -----------------------------------
def test_simple(tmp_path : Path):
    '''
    Simplest test
    '''
    grid = Grid(root = [])
    ptr  = GridPlotter(grid = grid)
    ptr.plot(
        randomize = False,
        path      = tmp_path / 'grid.png')
# -----------------------------------
