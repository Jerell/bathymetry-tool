from pathlib import Path

import pytest

SAMPLEDATA = Path(__file__).parent.parent / "sampledata"


@pytest.fixture
def spirit_pointz_path():
    return SAMPLEDATA / "spirit" / "KP_Points" / "KP_Points_1m"


@pytest.fixture
def spirit_polyline_path():
    return SAMPLEDATA / "spirit" / "MNZ_Export" / "MNZ_Export_Line"


@pytest.fixture
def calcasieu_kmz_path():
    return SAMPLEDATA / "calcasieu.kmz"
