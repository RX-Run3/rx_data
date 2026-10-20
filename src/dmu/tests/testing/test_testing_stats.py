import pytest

from typing      import Literal
from dmu.testing import stats
from dmu.stats   import zfit
from dmu.stats   import print_pdf

# ----------------------------------------------
@pytest.mark.parametrize('kind', ['s+b', 's+b+x', 's_alt+b'])
def test_get_pdfs_suffix(kind : Literal['s+b', 's+b+x', 's_alt+b']):
    '''
    Test PDF getting function 
    '''
    pdf = stats.get_model(
        kind        = kind, 
        suffix      = 'test',
        suffix_pdfs = True)

    assert isinstance(pdf, zfit.pdf.SumPDF)

    print_pdf(pdf)
# ----------------------------------------------
@pytest.mark.parametrize('kind', ['s+b', 's+b+x', 's_alt+b'])
def test_get_pdfs_prefix(kind : Literal['s+b', 's+b+x', 's_alt+b']):
    '''
    Test PDF getting function 
    '''
    pdf = stats.get_model(
        kind        = kind, 
        prefix      = 'test',
        suffix_pdfs = False)

    assert isinstance(pdf, zfit.pdf.SumPDF)

    print_pdf(pdf)
# ----------------------------------------------
@pytest.mark.parametrize('kind', ['signal_kde', 'skde+b'])
def test_get_pdf_kde(kind : Literal['signal_kde', 'skde+b']):
    '''
    Test creating model which uses a KDE
    '''
    pdf = stats.get_model(
        kind        = kind, 
        prefix      = 'test',
        suffix_pdfs = False)

    print_pdf(pdf)
# ----------------------------------------------
