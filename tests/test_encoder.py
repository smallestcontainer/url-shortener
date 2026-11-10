import pytest
from hashids import Hashids

from encoder import Encoder

SALT = "test salt"
MIN_LENGTH = 6


@pytest.fixture
def encoder():
    return Encoder(salt=SALT, min_length=MIN_LENGTH)


def test_known_hashes():
    e = Encoder("golden salt", min_length=6)
    assert e.encode(1) == "bPNnPd"
    assert e.encode(123456789) == "NgEp4L"


def test_same_salt_gives_same_hash_across_instances():
    # Hashes must survive a restart and match across replicas.
    a = Encoder(salt=SALT, min_length=MIN_LENGTH)
    b = Encoder(salt=SALT, min_length=MIN_LENGTH)
    assert a.encode(42) == b.encode(42)


def test_different_salt_gives_different_hash():
    a = Encoder(salt="salt a", min_length=MIN_LENGTH)
    b = Encoder(salt="salt b", min_length=MIN_LENGTH)
    assert a.encode(42) != b.encode(42)


@pytest.mark.parametrize("n", [0, 1, 61, 62, 10**9])
def test_roundtrip(encoder, n):
    assert encoder.decode(encoder.encode(n)) == n


@pytest.mark.parametrize("n", [0, 1, 10**9])
def test_min_length(encoder, n):
    assert len(encoder.encode(n)) >= MIN_LENGTH


def test_encode_negative_raises(encoder):
    with pytest.raises(ValueError, match="Negative"):
        encoder.encode(-1)


@pytest.mark.parametrize(
    "code",
    [
        pytest.param("", id="empty"),
        pytest.param("zzzzzz", id="garbage"),
        pytest.param(
            Hashids(salt=SALT, min_length=MIN_LENGTH).encode(1, 2),
            id="multiple-numbers",
        ),
        pytest.param(
            Encoder(salt="other salt", min_length=MIN_LENGTH).encode(1), id="other-salt"
        ),
    ],
)
def test_decode_invalid_raises(encoder, code):
    with pytest.raises(ValueError, match="Invalid code"):
        encoder.decode(code)
