import sys


def load(path):
    wrms, gdb = [], []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) < 3:
                continue
            wrms.append(float(p[2].split('=')[1]))
            gdb.append(float(p[3].split('=')[1]))
    return wrms, gdb


def show(title, wrms, pre, post, lo, hi):
    print('%s (20 ms windows, t = win*20 ms):' % title)
    print('win t_ms   wrms      pre_gdb  post_gdb delta(pre-post)')
    for i in range(lo, hi + 1):
        print('%2d  %3d  %8.6f %8.3f %8.3f %+7.3f' % (
            i, i * 20, wrms[i], pre[i], post[i], pre[i] - post[i]))


def main():
    pre_path, post_path = sys.argv[1], sys.argv[2]
    wrms_pre, gdb_pre = load(pre_path)
    wrms_post, gdb_post = load(post_path)
    assert wrms_pre == wrms_post, 'pre-leveler energy must be identical'
    wrms = wrms_pre
    show('initial voicing onset (h->E)', wrms, gdb_pre, gdb_post, 0, 4)
    show('stressed lateral onset (l->oU)', wrms, gdb_pre, gdb_post, 7, 13)
    d0 = gdb_pre[0] - gdb_post[0]
    print('initial onset: energy jump w0->w1; pre gain at w0 (t=0-20ms, '
          'before voicing) sits %+.3f dB vs causal -> %s' % (
              d0, 'PRE-DUCK (lead 20ms)' if d0 < -0.1 else 'no pre-duck'))
    for k, name in [(1, 'initial'), (11, 'stressed')]:
        pre_fall = max(gdb_pre[k - 1], gdb_pre[k]) - min(gdb_pre[k:k + 2])
        print('%s onset k=%d: post gain fall across k-1..k+1 = %.3f dB '
              '(causal tracking, lag 0ms vs first energy rise)' % (
                  name, k, max(gdb_post[k - 1], gdb_post[k]) -
                  min(gdb_post[k:k + 2])))


if __name__ == '__main__':
    main()
