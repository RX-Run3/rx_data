'''
Module with tests for RDFRenamer
'''
import pytest
import numpy
import pandas as pnd

from typing      import Final
from rx_data     import RDFRenamer
from dmu.testing import utilities as tut

_RNG : Final[numpy.random.Generator] = numpy.random.default_rng(seed = 42)

def test_dot_branches():
    '''
    Check if friend tree branches were renamed
    '''
    data = {
        'a' : _RNG.uniform(0, 1, size = 100),
        'b' : _RNG.uniform(0, 1, size = 100),
        'c' : _RNG.uniform(0, 1, size = 100),
    }

    df = pnd.DataFrame(data)

    rdf = tut.rdf_with_friend(df = df, branch = 'c')

    rnm = RDFRenamer()
    rdf = rnm.run(rdf = rdf)
    rdf.Display().Print()

    with pytest.raises(ValueError):
        rdf = rnm.run(rdf = rdf)
