import pytest

from tgstats import load_bands, pick_band
from tgstats.benchmark import compare


def test_bundled_data_has_five_bands():
    bands = load_bands()
    assert [b.key for b in bands] == ["1k-5k", "5k-20k", "20k-100k", "100k-500k", "500k+"]
    assert bands[0].median_reach == pytest.approx(0.31394)
    assert bands[-1].max_subscribers is None


@pytest.mark.parametrize(
    "subs,key",
    [
        (1000, "1k-5k"),
        (4999, "1k-5k"),
        (5000, "5k-20k"),
        (27900, "20k-100k"),
        (100000, "100k-500k"),
        (499999, "100k-500k"),
        (500000, "500k+"),
        (9940000, "500k+"),
    ],
)
def test_band_selection(subs, key):
    assert pick_band(subs).key == key


def test_below_floor_gives_no_band():
    assert pick_band(999) is None
    assert pick_band(0) is None


def test_compare_above_and_below():
    above = compare(27900, 0.30)
    assert above.available and above.band == "20k-100k"
    assert above.position == "above" and above.ratio == pytest.approx(0.30 / 0.09126)
    assert above.difference_points == pytest.approx(30.0 - 9.126)
    below = compare(2000, 0.10)
    assert below.position == "below" and below.band == "1k-5k"


def test_compare_under_1000_explains_why():
    c = compare(119, 0.5)
    assert not c.available
    assert "1,000" in c.reason and "119" in c.reason
    assert c.band is None


def test_compare_missing_inputs():
    assert not compare(None, 0.1).available
    assert not compare(5000, None).available


def test_attribution_present():
    c = compare(5000, 0.1).to_dict()
    assert c["attribution"] == "Pinlyx, Telegram Channel Reach 2026"
    assert c["license"] == "CC BY 4.0"
