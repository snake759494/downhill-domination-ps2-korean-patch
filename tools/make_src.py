"""번역 후보 목록: off, cap(제자리 최대 바이트), 참조유형, 원문"""
import json, re, struct, sys
sys.path.insert(0, 'tools')
import elf
D = elf.D; B = elf.BASE; GP = 0x2a40f0
LO, HI = 0x164d00, 0x194cf0
S = json.load(open('work/strings_all.json'))
# gp 상대 참조
gp = {}
for a in range(0x10a000, 0x263bc0, 4):
    w = elf.u32(a); op = w >> 26
    if op in (0x09, 0x23, 0x25, 0x24, 0x21) and ((w >> 21) & 31) == 28:
        v = GP + ((w & 0xffff) ^ 0x8000) - 0x8000 - B
        if LO <= v < HI:
            gp.setdefault(v, []).append(a)


def cap(off, end):
    p = end
    while p < HI and D[p] == 0:
        p += 1
    return p - off - 1


def esc(t):
    return t.replace('\\', '\\\\').replace('\n', '\\n').replace('\t', '\\t')


def texty(t):
    if sum(c.isalpha() for c in t) < 2:
        return False
    if sum(ord(c) >= 0x80 for c in t) > 2:
        return False
    return all(ord(c) >= 0x20 or c in '\n\t' for c in t)


seen = set(); rows = []
for s in S:
    o = s['off']
    if o in seen:
        continue
    seen.add(o)
    t = s['text']
    if not texty(t):
        continue
    refs = []
    if s['ptr']: refs.append('P%d' % len(s['ptr']))
    if s['code']: refs.append('C%d' % len(s['code']))
    if o in gp: refs.append('G%d' % len(gp[o]))
    rows.append((o, cap(o, s['end']), ''.join(refs) or '-', esc(t)))
with open('work/cand.tsv', 'w', encoding='utf-8') as f:
    for r in rows:
        f.write('%x\t%d\t%s\t%s\n' % r)
json.dump({hex(k): v for k, v in gp.items()}, open('work/gprefs.json', 'w'))
print(len(rows))
