'''
Module with tests for RegularGraph
'''

from dmu.generic import RegularGraphMaker
from gvar        import gvar

# -------------------------------
def _pick(coo : tuple[float,float]) -> bool:
    x, y = coo
    if x == 2 and y == 5:
        return True

    return False 
# -------------------------------
def test_simple():
    xs = [1., 2., 3.]
    ys = [4., 5., 6.]

    coordinates = [ (x, y) for x in xs for y in ys ]

    data = { coo : gvar(1,1) for coo in coordinates if _pick(coo = coo) }

    mkr = RegularGraphMaker(data = data)
    grp = mkr.get_graph()

