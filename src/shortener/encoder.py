from hashids import Hashids


class Encoder:
    def __init__(self, salt: str, min_length: int):
        self._enc = Hashids(salt=salt, min_length=min_length)

    def encode(self, num: int) -> str:
        if num < 0:
            raise ValueError(f"Negative number provided: {num!r}")

        return self._enc.encode(num)

    def decode(self, hash: str) -> int:
        data = self._enc.decode(hash)

        if len(data) != 1:
            raise ValueError(f"Invalid code: {hash!r}")

        return data[0]
