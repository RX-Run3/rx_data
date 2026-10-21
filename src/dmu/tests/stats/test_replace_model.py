import itertools

import pytest
import zfit

from dmu.stats import utilities as sut

_counter = itertools.count()


def _gauss(name: str, mu: float = 0.0) -> zfit.pdf.BasePDF:
    obs    = zfit.Space('x', limits=(-5, 5))
    idx    = next(_counter)  # zfit needs unique parameter names
    mu_par = zfit.Parameter(f'mu_{name}_{idx}', mu, -5, 5)
    sg_par = zfit.Parameter(f'sg_{name}_{idx}', 1.0, 0.1, 5)

    return zfit.pdf.Gauss(mu_par, sg_par, obs, name=name)


def test_replace_top_level():
    a, b, c = _gauss('a'), _gauss('b'), _gauss('c')
    new     = _gauss('new', mu=1.0)
    out     = sut.replace_model(models=[a, b, c], name='b', pdf=new)

    assert [p.name for p in out] == ['a', 'new', 'c']
    assert out[0] is a
    assert out[1] is new
    assert out[2] is c


def test_replace_modifies_and_returns_same_list():
    models = [_gauss('a'), _gauss('b')]
    out = sut.replace_model(models=models, name='a', pdf=_gauss('new'))

    assert out is models


def test_name_not_found():
    models = [_gauss('a'), _gauss('b')]

    with pytest.raises(ValueError, match='PDF missing not found'):
        sut.replace_model(models=models, name='missing', pdf=_gauss('new'))


def test_empty_list():
    with pytest.raises(ValueError, match='PDF a not found'):
        sut.replace_model(models=[], name='a', pdf=_gauss('new'))
