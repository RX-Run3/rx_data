from typing import Final
import pytest
import zfit

from dmu.stats import utilities as sut

_FRAC : Final[float] = 0.5
'''Used as fraction in sums of pdfs'''

@pytest.fixture(scope='module')
def pdfs():
    # Module scope: zfit rejects a second Parameter with the same name
    obs   = zfit.Space('x', limits=(-5, 5))
    mu    = zfit.Parameter('mu_test', 0.0)
    sigma = zfit.Parameter('sigma_test', 1.0)

    gauss_a = zfit.pdf.Gauss(mu, sigma, obs=obs, name='gauss_a')
    gauss_b = zfit.pdf.Gauss(mu, sigma, obs=obs, name='gauss_b')
    gauss_c = zfit.pdf.Gauss(mu, sigma, obs=obs, name='gauss_c')
    gauss_d = zfit.pdf.Gauss(mu, sigma, obs=obs, name='gauss_d')

    inner = zfit.pdf.SumPDF([gauss_a, gauss_b], fracs=[_FRAC], name='inner_sum')
    outer = zfit.pdf.SumPDF([inner  , gauss_c], fracs=[_FRAC], name='outer_sum')

    return {
        'a'     : gauss_a,
        'b'     : gauss_b,
        'c'     : gauss_c,
        'd'     : gauss_d,
        'inner' : inner,
        'outer' : outer,
    }


def test_found_at_top_level(pdfs):
    result = sut.find_model(models=[pdfs['a'], pdfs['b']], name='gauss_b')

    assert result is pdfs['b']


def test_sum_itself_can_be_found(pdfs):
    result = sut.find_model(models=[pdfs['inner']], name='inner_sum')

    assert result is pdfs['inner']


def test_found_inside_sum(pdfs):
    result = sut.find_model(models=[pdfs['inner']], name='gauss_a')

    assert result is pdfs['a']


def test_found_inside_nested_sum(pdfs):
    result = sut.find_model(models=[pdfs['outer']], name='gauss_b')

    assert result is pdfs['b']


def test_found_after_sum_that_does_not_contain_it(pdfs):
    # Regression: a miss inside the first SumPDF must not abort the search
    result = sut.find_model(models=[pdfs['inner'], pdfs['d']], name='gauss_d')

    assert result is pdfs['d']


def test_found_in_second_sum_after_miss_in_first(pdfs):
    result = sut.find_model(models=[pdfs['inner'], pdfs['outer']], name='gauss_c')

    assert result is pdfs['c']


def test_not_found_raises(pdfs):
    with pytest.raises(ValueError, match='missing_pdf'):
        sut.find_model(models=[pdfs['a'], pdfs['outer']], name='missing_pdf')


def test_empty_list_raises():
    with pytest.raises(ValueError, match='anything'):
        sut.find_model(models=[], name='anything')
