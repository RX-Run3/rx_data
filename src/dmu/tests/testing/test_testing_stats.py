import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import pytest

from typing      import Literal
from dmu.testing import stats
from dmu.stats   import zfit

# ----------------------------------------------
@pytest.mark.parametrize('kind', ['s+b', 's+b+x', 's_alt+b'])
def test_get_pdfs(kind : Literal['s+b', 's+b+x', 's_alt+b']):
    '''
    Test PDF getting function 
    '''
    pdf = stats.get_model(kind = kind)

    assert isinstance(pdf, zfit.pdf.SumPDF)
# ----------------------------------------------
