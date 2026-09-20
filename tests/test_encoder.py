import pytest
from encoder import Encoder


@pytest.fixture
def encoder():
    return Encoder(salt="test salt", min_length=6)


def test_known_hashes():
    e = Encoder("golden salt", min_length=6)
    assert e.encode(1) == "bPNnPd"
    assert e.encode(123456789) == "NgEp4L"


def test_determinism(encoder):
    assert encoder.encode(1) == encoder.encode(1)
    hash = encoder.encode(1)
    assert encoder.decode(hash) == encoder.decode(hash)


def test_roundtrip(encoder):
    for n in [0, 1, 61, 62, 10**9]:
        assert encoder.decode(encoder.encode(n)) == n
