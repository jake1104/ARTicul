import numpy as np

from articul._articul import lookup_features as _lookup
from articul._articul import synthesize as _synthesize


def lookup(symbol):
    return _lookup(symbol)


def synthesize(text, sample_rate=22050, f0=120.0):
    return np.array(
        _synthesize(text, int(sample_rate), float(f0)), dtype=np.float32
    )
