import wave, hashlib
a = open('probe/0.0.0.23.3/regression-a.wav','rb').read()
b = open('probe/0.0.0.23.3/regression-b.wav','rb').read()
na = wave.open('probe/0.0.0.23.3/regression-a.wav').getnframes()
nb = wave.open('probe/0.0.0.23.3/regression-b.wav').getnframes()
exp = 'B832514D56698CCE417ED3D16BA549312C7AB8573811457FFF49A12107C24620'
print('fixed sentence TIs TIN default voice 22050Hz')
print('regression-a: samples=%d bytes=%d sha256=%s' % (na, len(a), hashlib.sha256(a).hexdigest()))
print('regression-b: samples=%d bytes=%d sha256=%s' % (nb, len(b), hashlib.sha256(b).hexdigest()))
print('determinism byte-identical: %s' % (a == b))
print('expected 8822 samples: %s' % (na == 8822 and nb == 8822))
print('expected hash %s match: %s' % (exp, hashlib.sha256(a).hexdigest().upper() == exp))
