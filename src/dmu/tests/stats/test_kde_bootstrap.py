from typing import Final
import numpy as np
import pytest
import zfit

from dmu.stats import utilities as sut

_KDE_CLASSES = [
    zfit.pdf.KDE1DimExact,
    zfit.pdf.KDE1DimFFT,
    zfit.pdf.KDE1DimISJ,
]

_N_POINTS = 2000
X = np.linspace(-5, 5, 200)

_TOLERANCE : Final[float] = 0.05


@pytest.fixture(scope="module")
def obs() -> zfit.Space:
    return zfit.Space("x", limits=(-5, 5))


@pytest.fixture(scope="module")
def values() -> np.ndarray:
    rng = np.random.default_rng(42)
    return np.clip(rng.normal(0.0, 1.5, size=_N_POINTS), -4.99, 4.99)


@pytest.fixture(scope="module")
def data(obs: zfit.Space, values: np.ndarray) -> zfit.Data:
    data = zfit.Data.from_numpy(obs=obs, array=values)
    if not isinstance(data, zfit.Data):
        raise ValueError('Invalid data')

    return data


def make_kde(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> sut.AnyKDE:
    if issubclass(cls, zfit.pdf.KDE1DimISJ):
        return cls(data, obs=obs)

    return cls(data, obs=obs, bandwidth=0.3)


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_returns_same_class_and_observable(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde = make_kde(cls, data, obs)

    new_pdf = sut.bootstrap_kde(pdf=kde, index=0)

    assert type(new_pdf) is cls
    assert new_pdf.space == kde.space


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_same_index_is_reproducible(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde = make_kde(cls, data, obs)

    first = sut.bootstrap_kde(pdf=kde, index=7)
    second = sut.bootstrap_kde(pdf=kde, index=7)

    np.testing.assert_allclose(first.pdf(X).numpy(), second.pdf(X).numpy())


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_different_index_gives_different_replica(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde = make_kde(cls, data, obs)

    first  = sut.bootstrap_kde(pdf=kde, index=1)
    second = sut.bootstrap_kde(pdf=kde, index=2)

    assert not np.allclose(first.pdf(X).numpy(), second.pdf(X).numpy())


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_weights_are_poisson_counts_with_unit_mean(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde     = make_kde(cls, data, obs)
    new_pdf = sut.bootstrap_kde(pdf=kde, index=9)

    weights = new_pdf._weights.numpy()  # pyrefly: ignore

    assert np.all(weights >= 0)
    np.testing.assert_allclose(weights, np.round(weights))
    # The sum of N Poisson(1) draws has mean N and standard deviation sqrt(N).
    assert abs(weights.sum() - _N_POINTS) < 5 * np.sqrt(_N_POINTS)


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_replica_is_a_valid_pdf_close_to_original(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde = make_kde(cls, data, obs)

    new_pdf = sut.bootstrap_kde(pdf=kde, index=4)

    original = kde.pdf(X).numpy()
    replica = new_pdf.pdf(X).numpy()
    assert np.all(np.isfinite(replica))
    assert np.all(replica >= 0)
    assert np.max(np.abs(replica - original)) < _TOLERANCE


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_original_kde_is_untouched(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde = make_kde(cls, data, obs)
    before = kde.pdf(X).numpy()

    sut.bootstrap_kde(pdf=kde, index=5)

    np.testing.assert_allclose(kde.pdf(X).numpy(), before)


@pytest.mark.parametrize("cls", [c for c in _KDE_CLASSES if c is not zfit.pdf.KDE1DimISJ])
def test_bandwidth_is_preserved(cls: type[sut.AnyKDE], data: zfit.Data, obs: zfit.Space) -> None:
    kde = make_kde(cls, data, obs)

    new_pdf = sut.bootstrap_kde(pdf=kde, index=6)

    assert float(new_pdf._bandwidth) == pytest.approx(0.3)  # pyrefly: ignore


@pytest.mark.parametrize("cls", _KDE_CLASSES)
def test_original_weights_are_multiplied_by_the_counts(cls: type[sut.AnyKDE], obs: zfit.Space) -> None:
    values   = np.linspace(-4.9, 4.9, _N_POINTS)  # all distinct, so values identify events
    weights  = 1.0 + np.arange(_N_POINTS) / _N_POINTS
    weighted = zfit.Data.from_numpy(obs=obs, array=values, weights=weights)
    if not isinstance(weighted, zfit.Data):
        raise ValueError('Invalid data')

    kde     = make_kde(cls, weighted, obs)
    new_pdf = sut.bootstrap_kde(pdf=kde, index=8)

    old_values  : list[float] = kde._data.numpy().tolist()    # pyrefly: ignore
    old_weights : list[float] = kde._weights.numpy().tolist() # pyrefly: ignore

    original                  = dict(zip(old_values, old_weights, strict = True))
    new_values  : list[float] = new_pdf._data.numpy().tolist()  # pyrefly: ignore
    new_weights : list[float] = new_pdf._weights.numpy().tolist()  # pyrefly: ignore

    for value, weight in zip(new_values, new_weights, strict = True):
        count = weight / original[value]
        assert count == pytest.approx(round(count))
        assert round(count) >= 0
