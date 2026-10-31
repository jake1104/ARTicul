import wave, hashlib
a = open('probe/0.0.0.24.3/regression-a.wav','rb').read()
b = open('probe/0.0.0.24.3/regression-b.wav','rb').read()
na = wave.open('probe/0.0.0.24.3/regression-a.wav').getnframes()
nb = wave.open('probe/0.0.0.24.3/regression-b.wav').getnframes()
exp = '2AD4F8413C9182F0BE39B9AC836AAE06233272C3367256A6F859FA0AE44AD141'
print('fixed sentence TIs TIN default voice 22050Hz')
print('regression-a: samples=%d bytes=%d sha256=%s' % (na, len(a), hashlib.sha256(a).hexdigest()))
print('regression-b: samples=%d bytes=%d sha256=%s' % (nb, len(b), hashlib.sha256(b).hexdigest()))
print('determinism byte-identical: %s' % (a == b))
print('expected 8822 samples: %s' % (na == 8822 and nb == 8822))
print('expected hash %s match: %s' % (exp, hashlib.sha256(a).hexdigest().upper() == exp))
