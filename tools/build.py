"""다운힐 도미네이션(SCUS-97177) 한글 패치 빌드

원본 ISO -> Downhill Domination (Korean).iso
 1. translation/ko_*.tsv 를 읽어 2바이트 한글 코드로 인코딩
 2. ELF 문자열 교체(제자리 또는 재배치 후 포인터/코드 참조 수정)
 3. ELF 텍스트 루틴 패치(2바이트 디코드, 한글 글자는 TEX0 를 4HH 로 바꿔 그림)
 4. 폰트가 든 RTX(SHELL/UI, LVL/*) 에 한글 4HH 텍스처 레코드 3개 추가
 5. ISO 재구성(커진 파일은 이미지 끝으로 옮기고 ISO9660/UDF 갱신)
"""
import collections
import glob
import json
import os
import re
import shutil
import struct
import sys
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import asm      # noqa: E402
import kfont    # noqa: E402
import ie       # noqa: E402
import rtx      # noqa: E402
import udf      # noqa: E402

SRC_ISO = os.path.join(ROOT, 'Downhill Domination (USA).iso')
OUT_ISO = os.path.join(ROOT, 'Downhill Domination (Korean).iso')
SEC = 2048
BASE = 0x109000                 # vaddr = file offset + BASE
LO, HI = 0x164d00, 0x194cf0     # 문자열 영역(파일 오프셋)
RODATA = 0x17f880               # 이 앞은 .data (구조체 섞임)

LEAD0, NLEAD = 0xF0, 7          # 한글: 선두 0xF0~0xF6, 후속 0xA0~0xFF (0x80~0x9F 는 아이콘 대역이라 피함)
Y0 = 65                         # 한글 셀 시작 y (위 64줄은 다른 4HH 텍스처와 겹침)

# 디버그 전용 문자열 영역(덮어써도 됨) — 재배치 문자열/코드 풀
# 빈 printf(무동작)에만 넘겨지는 디버그 문자열 위치(시작, 널 위치) — 덮어써도 동작에 영향 없음(검증한 목록)
DEBUG_STRINGS = [
    (0x180a58, 0x180a60),
    (0x1814f0, 0x1814f8),
    (0x1860d8, 0x1860f1),
    (0x18ee40, 0x18ee64),
    (0x18ee68, 0x18ee8b),
    (0x18ee90, 0x18eeb4),
    (0x18eef0, 0x18ef15),
    (0x18ef50, 0x18ef65),
    (0x18ef68, 0x18ef91),
    (0x18efa8, 0x18efc3),
    (0x18efc8, 0x18f00f),
    (0x18f010, 0x18f047),
    (0x18f048, 0x18f071),
    (0x18f078, 0x18f0a7),
    (0x18f158, 0x18f1a8),
    (0x18f400, 0x18f429),
    (0x18f430, 0x18f468),
    (0x18f498, 0x18f4b4),
    (0x18f4b8, 0x18f4d6),
    (0x18f4d8, 0x18f4fb),
    (0x18f500, 0x18f541),
    (0x18f5c8, 0x18f606),
    (0x18f608, 0x18f638),
    (0x18f6e8, 0x18f737),
    (0x18f7a8, 0x18f7bb),
    (0x18f7f0, 0x18f811),
    (0x18f818, 0x18f862),
    (0x18f868, 0x18f887),
    (0x18f888, 0x18f8ba),
    (0x18f8c0, 0x18f8f7),
    (0x18f940, 0x18f974),
    (0x193480, 0x193485),
]
FOREIGN = (0x18bad8, 0x18bcf8)      # 외국어 라이더 선택 문자열(북미판 미사용) — 풀로 사용

# 텍스트 루틴 주소
SLOT, PTR, TAG, CNT, STATE, TEX0P = 0x4f3570, 0x513ac0, 0x513ad0, 0x513ae0, 0x513af0, 0x4f35b0
DRAWCHAR, KERN, OFFX, OFFY = 0x20fdb0, 0x20f6c0, 0x23d618, 0x23d650


# ------------------------------------------------------------------ 번역
def load_ko():
    ko = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'translation', 'ko_*.tsv'))):
        for n, l in enumerate(open(f, encoding='utf-8'), 1):
            l = l.rstrip('\n')
            if not l.strip() or l.startswith('#'):
                continue
            k, t = l.split('\t', 1)
            off = int(k, 16)
            assert off not in ko, (f, n, k)
            ko[off] = t
    return ko


def tokens(t):
    """이스케이프 해석 -> 토큰 목록 (str 문자 또는 int 원시 바이트)"""
    out = []
    i = 0
    while i < len(t):
        c = t[i]
        if c == '\\' and i + 1 < len(t):
            n = t[i + 1]
            out.append({'n': '\n', 't': '\t', '\\': '\\'}[n])
            i += 2
        elif c == '{' and re.match(r'\{[0-9a-f]{2}\}', t[i:i + 4]):
            out.append(int(t[i + 1:i + 3], 16))
            i += 4
        else:
            out.append(c)
            i += 1
    return out


def is_hangul(c):
    return isinstance(c, str) and '가' <= c <= '힣'


def encode(toks, code):
    b = bytearray()
    for c in toks:
        if isinstance(c, int):
            b.append(c)
        elif is_hangul(c):
            g = code[c]
            b += bytes((LEAD0 + g // 96, 0xA0 + g % 96))
        elif c == '®':
            b.append(0xae)
        else:
            o = ord(c)
            assert 0x20 <= o < 0x7f or c in '\n\t', ('허용 안 되는 문자', c)
            b.append(o)
    return bytes(b)


FMT = re.compile(rb'%[-+ 0#]*[0-9]*(?:\.[0-9]+)?[sdxXfcui%]')


# ------------------------------------------------------------------ ELF 문자열 참조
def scan_refs(D):
    ptrs = collections.defaultdict(list)
    for o in range(LO, HI, 4):
        v = struct.unpack_from('<I', D, o)[0] - BASE
        if LO <= v < HI:
            ptrs[v].append(o)
    code = collections.defaultdict(list)
    gp = collections.defaultdict(list)
    regs = {}
    for o in range(0x1000, 0x15abc0, 4):
        w = struct.unpack_from('<I', D, o)[0]
        op = w >> 26
        if op == 0x0f:
            regs[(w >> 16) & 31] = (w & 0xffff, o)
        elif op == 0x09:
            rs = (w >> 21) & 31
            if rs == 28:
                v = 0x2a40f0 + ((w & 0xffff) ^ 0x8000) - 0x8000 - BASE
                if LO <= v < HI:
                    gp[v].append(o)
            elif rs in regs and o - regs[rs][1] < 0x100:
                v = (regs[rs][0] << 16) + ((w & 0xffff) ^ 0x8000) - 0x8000 - BASE
                if LO <= v < HI:
                    code[v].append((regs[rs][1], o))
        elif op in (0x23, 0x24, 0x25, 0x20, 0x21) and ((w >> 21) & 31) == 28:
            v = 0x2a40f0 + ((w & 0xffff) ^ 0x8000) - 0x8000 - BASE
            if LO <= v < HI:
                gp[v].append(o)
    return ptrs, code, gp


def debug_strings(D, code):
    """코드에서만 참조되고, 참조 직후 호출이 전부 빈 함수(인자 저장 후 복귀 = 무동작 printf)인 문자열
    -> [(시작, 끝)] (끝 = 널 위치).  이 자리는 덮어써도 동작에 영향이 없다."""
    def u32(va):
        return struct.unpack_from('<I', D, va - BASE)[0]

    def nextjal(va):
        for k in range(10):
            w = u32(va + 4 * k)
            if w >> 26 == 3:
                return (w & 0x3ffffff) << 2
        return None

    def is_empty(f):
        for k in range(40):
            w = u32(f + 4 * k)
            op = w >> 26
            if w == 0x03e00008:
                return True
            if op in (0x3f, 0x39, 0x2b) and ((w >> 21) & 31) == 29:
                continue
            if op == 0x09 and ((w >> 21) & 31) == 29 and ((w >> 16) & 31) == 29:
                continue
            return False
        return False
    ptrset = set()
    for o in range(LO, HI, 4):
        v = struct.unpack_from('<I', D, o)[0] - BASE
        if LO <= v < HI:
            ptrset.add(v)
    out = []
    for off, refs in code.items():
        if off in ptrset:
            continue
        ts = [nextjal(addiu + BASE) for _, addiu in refs]
        if all(t and t < 0x263bc0 and is_empty(t) for t in ts):
            out.append((off, D.index(b'\0', off)))
    return sorted(out)


def cstr(D, off):
    e = D.index(b'\0', off)
    return bytes(D[off:e])


def capacity(D, off, n_orig, refstarts):
    """제자리 최대 바이트(널 제외). .data 영역은 원문 길이까지만."""
    p = off + n_orig
    while p < HI and D[p] == 0:
        p += 1
    cap = p - off - 1
    if off < RODATA:
        # .data: 다음 칸도 문자열(문자열 배열)일 때만 0 패딩까지 사용
        nxt = bytes(D[p:p + 4])
        if not (len(nxt) == 4 and all(0x20 <= b < 0x7f for b in nxt)):
            cap = n_orig
    # 안쪽에 다른 참조 시작점이 있으면 거기까지
    for r in refstarts:
        if off < r <= off + cap:
            cap = min(cap, r - off - 1)
    return cap


# ------------------------------------------------------------------ 패치 코드
def patch_code_src():
    src = f'''
#@piece ds
# ---- drawString 의 기본 문자 분기 대체 (0x20fd68 에서 점프해 옴)
ds_stub:
  lbu a2, 0(s0)
  sltiu t0, a2, 0xf0
  bne t0, zero, ds_call
  nop
  sltiu t0, a2, {LEAD0 + NLEAD}
  beq t0, zero, ds_call
  nop
  lbu t1, 1(s0)
  beq t1, zero, ds_call
  nop
  addiu a2, a2, -{LEAD0}
  sll t2, a2, 6
  sll a2, a2, 5
  addu a2, a2, t2
  addu a2, a2, t1
  addiu a2, a2, 0x60
  addiu s0, s0, 1
ds_call:
  move a1, s3
  jal dc_wrap
  move a0, s2
  move a1, v0
  j 0x20fd80
  addiu a2, s0, 1

dc_wrap:
  sltiu t0, a2, 0x100
  bne t0, zero, dc_latin
  nop
  j kdraw
  nop
dc_latin:
  j {DRAWCHAR}
  nop

#@piece km
# ---- 문자열 폭 측정(0x20f944 의 jal 대체): 한글은 adv + adv/16
km:
  sltiu t0, a0, 0xf0
  bne t0, zero, km_orig
  nop
  sltiu t0, a0, {LEAD0 + NLEAD}
  beq t0, zero, km_orig
  nop
  lbu t1, 1(s1)
  beq t1, zero, km_orig
  nop
  addiu s1, s1, 1
  sw zero, 0(a1)
  jr ra
  move v0, zero
km_orig:
  j {KERN}
  nop

#@piece kd
# ---- 한글 글자 그리기: a0=슬롯, a1=ctx, a2=0x100+글리프번호
kdraw:
  addiu sp, sp, -0x70
  sd ra, 0x60(sp)
  sd s0, 0x20(sp)
  sd s1, 0x28(sp)
  sd s2, 0x30(sp)
  sd s3, 0x38(sp)
  sd s4, 0x40(sp)
  sd s5, 0x48(sp)
  sll t0, a0, 5
  la t1, {SLOT}
  addu s1, t0, t1
  move s2, a1
  addiu s3, a2, -0x100
  move a0, s2
  addiu a1, sp, 4
  jal {OFFX}
  addiu a2, sp, 8
  move a0, s2
  addiu a1, sp, 0xc
  jal {OFFY}
  addiu a2, sp, 0x10
  lw v1, 4(sp)
  lw v0, 0xc(sp)
  sll v1, v1, 4
  sll v0, v0, 3
  subu s5, v1, v0
  lw a1, 8(sp)
  lw a0, 0x10(sp)
  sll a1, a1, 4
  sll a0, a0, 3
  subu s4, a1, a0
  sll t9, s2, 2
  la t0, {STATE}
  addu t0, t0, t9
  lw t1, 0(t0)
  li t2, 2
  bne t1, t2, kd_nobatch
  nop
  la t3, {TAG}
  addu t3, t3, t9
  lw t3, 0(t3)
  la t4, {CNT}
  addu t4, t4, t9
  lhu t5, 0(t4)
  sh t5, 0(t3)
  sw zero, 0(t4)
kd_nobatch:
# 상태 3: 열린 배치 없음(1 은 '직전 qword 가 헤더'라 색 변경 시 되감김).
# 태그 포인터는 카운터 자신을 가리켜 닫기 때의 nloop 기록이 무해하게.
  li t2, 3
  sw t2, 0(t0)
  la t3, {TAG}
  addu t3, t3, t9
  la t4, {CNT}
  addu t4, t4, t9
  sw t4, 0(t3)
  sw zero, 0(t4)
  la t0, {PTR}
  addu t0, t0, t9
  lw s0, 0(t0)
  la t1, {TEX0P}
  addu t1, t1, t9
  lw t1, 0(t1)
  ld t2, 0(t1)
  lui t3, 0x03f0
  nor t3, t3, zero
  and t3, t2, t3
  lui t4, 0x02c0
  or t3, t3, t4
  li t5, 1
  lui t6, 0x6400
  dsll32 t6, t6, 0
  or t5, t5, t6
  lui t6, 0x65
  ori t6, t6, 0x3d36
  sd t5, 0(s0)
  sd t6, 8(s0)
  sd t3, 16(s0)
  sd t2, 56(s0)
# UV: col = k%{kfont.COLS}, row = k/{kfont.COLS}
  li t0, 2731
  mul t0, s3, t0
  srl t0, t0, 16
  li t1, {kfont.COLS}
  mul t1, t0, t1
  subu t1, s3, t1
  li t2, {kfont.PITCH * 16}
  mul t1, t1, t2
  mul t0, t0, t2
  addiu t1, t1, 8
  addiu t0, t0, {Y0 * 16 + 8}
  sll t2, t0, 16
  or t2, t2, t1
  sw t2, 24(s0)
  sw zero, 28(s0)
  addiu t1, t1, {kfont.CELL * 16}
  addiu t0, t0, {kfont.CELL * 16}
  sll t2, t0, 16
  or t2, t2, t1
  sw t2, 40(s0)
  j kd_xy
  sw zero, 44(s0)
#@piece kd2
kd_xy:
# XY
  lhu t4, 8(s1)
  lhu t5, 0xa(s1)
  lhu t0, 0x10(s1)
  lhu t1, 0x12(s1)
  addu t0, t0, s5
  addu t1, t1, s4
  srl t2, t4, 5
  addu t0, t0, t2
  li t2, 5
  mul t2, t5, t2
  srl t2, t2, 5
  addu t1, t1, t2
  li t2, 24
  mul t6, t4, t2
  srl t6, t6, 5
  mul t7, t5, t2
  srl t7, t7, 5
  lui t8, 0xff
  ori t8, t8, 0xffff
  sh t0, 32(s0)
  sh t1, 34(s0)
  sw t8, 36(s0)
  addu t0, t0, t6
  addu t1, t1, t7
  sh t0, 48(s0)
  sh t1, 50(s0)
  sw t8, 52(s0)
  addiu s0, s0, 64
  la t0, {PTR}
  addu t0, t0, t9
  sw s0, 0(t0)
# 진행: adv + adv/16
  lhu t0, 0xe(s1)
  lhu t1, 0x10(s1)
  addu t1, t1, t0
  sh t1, 0x10(s1)
  move v0, zero
  ld ra, 0x60(sp)
  ld s0, 0x20(sp)
  ld s1, 0x28(sp)
  ld s2, 0x30(sp)
  ld s3, 0x38(sp)
  ld s4, 0x40(sp)
  ld s5, 0x48(sp)
  jr ra
  addiu sp, sp, 0x70
'''
    pieces = {}
    for chunk in src.split('#@piece ')[1:]:
        name, body = chunk.split('\n', 1)
        pieces[name.strip()] = body
    return pieces


def assemble_pieces(bases):
    """bases: {조각: 주소} -> ({조각: 바이트}, 심볼)"""
    pieces = patch_code_src()
    labels = set()
    for body in pieces.values():
        labels |= set(re.findall(r'^\s*([A-Za-z_]\w*):', body, re.M))
    syms = {l: 0x200000 for l in labels}
    for _ in range(2):
        new = {}
        for name, body in pieces.items():
            a = asm.Asm(bases.get(name, 0x200000), syms)
            a.assemble(body)
            new.update({k: v for k, v in a.syms.items() if k in labels and k in re.findall(r'^\s*([A-Za-z_]\w*):', body, re.M)})
        syms.update(new)
    out = {name: asm.Asm(bases.get(name, 0x200000), syms).assemble(body) for name, body in pieces.items()}
    return out, syms


# ------------------------------------------------------------------ ELF
class Pool:
    def __init__(self, ranges):
        self.free = sorted(ranges)

    def alloc(self, n, align=1, hi=None):
        for i, (s, e) in enumerate(self.free):
            lo_, hi_ = s, e
            if hi is not None:      # (p + BASE + 0x8000) >> 16 == hi 인 범위로 제한
                lo_ = max(lo_, (hi << 16) - 0x8000 - BASE)
                hi_ = min(hi_, (hi << 16) + 0x8000 - BASE)
            p = (lo_ + align - 1) // align * align
            if p + n <= hi_:
                self.free[i:i + 1] = [r for r in ((s, p), (p + n, e)) if r[1] > r[0]]
                return p
        raise RuntimeError('풀 부족 n=%d hi=%s' % (n, hi))


def build_elf(D, ko, code_map):
    D = bytearray(D)
    ptrs, code, gp = scan_refs(D)
    refstarts = set(ptrs) | set(code) | set(gp)
    stat = collections.Counter()
    plan = {}
    for off, t in sorted(ko.items()):
        orig = cstr(D, off)
        assert orig, hex(off)
        toks = tokens(t)
        if toks and toks[0] == '@':      # 값 위치 고정: '@왼쪽|오른쪽'
            s = ''.join(x if isinstance(x, str) else '\0' for x in toks[1:])
            i = toks.index('|')
            left = encode(toks[1:i], code_map)
            right = encode(toks[i + 1:], code_map)
            plen = orig.rfind(right)
            assert plen >= 0, (hex(off), orig, right)
            assert len(left) <= plen, (hex(off), '왼쪽이 김', len(left), plen)
            new = left + b' ' * (plen - len(left)) + orig[plen:]
        else:
            new = encode(toks, code_map)
        # 이름 삽입용 공백 패딩 문자열: 접두부 길이를 원문과 같게
        m = re.match(rb'^(.*?\S)( {4,})$', orig)
        if m:
            pre = len(m.group(1))
            nb = new.rstrip(b' ')
            assert len(nb) <= pre, (hex(off), '이름 자리 접두부가 김', len(nb), pre)
            new = nb + b' ' * (len(orig) - len(nb))
        fo, fn = FMT.findall(orig), FMT.findall(new)
        assert fo == fn, (hex(off), '서식 불일치', fo, fn)
        cap = capacity(D, off, len(orig), refstarts)
        plan[off] = (orig, new, cap)
    # 다른 번역 문자열의 원래 범위 안에 있는 시작점은 재배치 필수
    inner = set()
    offs = sorted(plan)
    for o in offs:
        n = len(plan[o][0])
        for o2 in offs:
            if o < o2 < o + n:
                inner.add(o2)
    place = {}
    reloc = []
    errs = []
    for off in offs:
        orig, new, cap = plan[off]
        if off not in inner and len(new) <= cap:
            place[off] = off
            stat['inplace'] += 1
        elif (ptrs.get(off) or code.get(off)) and not gp.get(off):
            reloc.append(off)
        else:
            errs.append('%x\t재배치 불가: %d > %d\t%r' % (off, len(new), cap, orig))
    if errs:
        print('\n'.join(errs))
        raise SystemExit('오류 %d건' % len(errs))
    # 풀: 빈 printf 에만 쓰이는 디버그 문자열 + 외국어 라이더 선택 문자열(포인터를 영어로 돌림)
    #     + 재배치로 빈 원래 자리.  (PCSX2 는 두 번째 PT_LOAD 를 적재하지 않으므로 기존 세그먼트만 사용)
    chunks = [(o, e + 1) for o, e in DEBUG_STRINGS] + [FOREIGN]
    for off in reloc:
        orig = plan[off][0]
        end = off + len(orig) + 1
        if off not in inner and not any(off < r < end for r in refstarts):
            chunks.append((off, end))
    # 사이가 0 패딩뿐이고 다른 참조 시작점이 없으면 이웃 칸을 합친다
    chunks.sort()
    merged = []
    for s, e in chunks:
        if merged:
            ps, pe = merged[-1]
            gap = D[pe:s]
            if s >= pe and s - pe < 64 and not any(gap) and not any(pe <= r < s for r in refstarts):
                merged[-1] = (ps, max(pe, e))
                continue
        merged.append((s, e))
    pool = Pool(merged)
    print('풀 칸', len(merged), '최대', max(e - s for s, e in merged), '합계', sum(e - s for s, e in merged))
    part = os.environ.get('DD_ELF', 'all')     # 분할 시험용: all / str / code / none
    sizes, _ = assemble_pieces({})
    bases = {}
    for name in sorted(sizes, key=lambda n: -len(sizes[n])):     # 큰 조각부터
        bases[name] = pool.alloc(len(sizes[name]), 8) + BASE
    blobs, syms = assemble_pieces(bases)
    newva = {}
    # 코드 참조(상위 16비트 고정) 먼저, 그다음 긴 것부터
    for off in sorted(reloc, key=lambda o: (not code.get(o), -len(plan[o][1]))):
        orig, new, cap = plan[off]
        hi = None
        if code.get(off):
            hi = (off + BASE + 0x8000) >> 16
            luis = set(struct.unpack_from('<I', D, l)[0] & 0xffff for l, _ in code[off])
            assert luis == {hi}, (hex(off), luis)
        newva[off] = pool.alloc(len(new) + 1, 1, hi) + BASE
        stat['reloc'] += 1
    if part in ('code', 'none'):
        place, newva = {}, {}
    # 쓰기: 제자리 문자열은 원래 범위를 지우고 새 내용
    for off in place:
        orig, new, cap = plan[off]
        D[off:off + len(orig) + 1] = b'\0' * (len(orig) + 1)
    for off in place:
        orig, new, cap = plan[off]
        D[off:off + len(new) + 1] = new + b'\0'
    for off, va in newva.items():
        orig, new, cap = plan[off]
        D[va - BASE:va - BASE + len(new) + 1] = new + b'\0'
        for po in ptrs.get(off, []):
            struct.pack_into('<I', D, po, va)
        for lui, addiu in code.get(off, []):
            w = struct.unpack_from('<I', D, addiu)[0]
            struct.pack_into('<I', D, addiu, (w & 0xffff0000) | (va & 0xffff))
    # 외국어 라이더 선택 포인터 -> 영어(한글) 쪽과 같게
    for g in (0x16c73c, 0x16c754, 0x16c76c, 0x16c784):
        for k in range(4):
            struct.pack_into('<I', D, g + 4 * k, struct.unpack_from('<I', D, 0x16c728 + 4 * k)[0])
    for name, b in blobs.items():
        D[bases[name] - BASE:bases[name] - BASE + len(b)] = b

    def put(va, src):
        b = asm.Asm(va, syms).assemble(src)
        D[va - BASE:va - BASE + len(b)] = b
    hooks = os.environ.get('DD_HOOKS', 'ds,km').split(',')   # 분할 시험용
    if part not in ('str', 'none'):
        if 'ds' in hooks:
            put(0x20fd68, f'j {syms["ds_stub"]}\nnop')
        if 'km' in hooks:
            put(0x20f944, f'jal {syms["km"]}')
    print('문자열: 제자리 %d, 재배치 %d, 코드 %s' % (stat['inplace'], stat['reloc'], {k: hex(v) for k, v in bases.items()}))
    print('풀 남음', sum(e - s for s, e in pool.free))
    return bytes(D)


# ------------------------------------------------------------------ RTX
def hh_records(page, font):
    """한글 페이지(y>=64)를 3개 4HH 레코드로 (y64 512x64, y128 512x128, y256 512x256)"""
    recs = []
    tbp = font['b'] >> 16
    for y, th, tid in ((64, 6, 997), (128, 7, 998), (256, 8, 999)):
        h = 1 << th
        data = kfont.pack4(page[y:y + h])
        words = (0x80 + len(data)) // 4
        qw = (len(data) + 0x60) // 16
        hdr = bytearray(0x80)
        btbp = tbp + (y // 32) * 8 * 32
        c = (font['c'] & ~0xf03f) | 0x2c | (th << 12)
        struct.pack_into('<IIII', hdr, 0, words, 0x4b4f0000 | tid, (btbp << 16) | tid, c)
        struct.pack_into('<II', hdr, 0x10, 0x60000000 | qw, 0)
        struct.pack_into('<II', hdr, 0x18, 0, 0x50000000 | qw)
        recs.append(bytes(hdr) + data)
    return recs


def patch_rtx(u, page):
    ents, end = rtx.entries(u)
    fi = [k for k, x in enumerate(ents) if (x['c'] & 0x3f) == 0x24 and x['words'] == 0x8020]
    assert len(fi) == 1
    f = ents[fi[0]]
    ins = f['off'] + f['words'] * 4
    return u[:ins] + b''.join(hh_records(page, f)) + u[ins:]


def patch_loadbar(u, page):
    """LOADBAR RTX(비압축): 폰트가 마지막 레코드(크기 0 = 나머지 전부) — 그 앞에 한글 레코드 삽입"""
    p = 0
    while p + 16 <= len(u):
        n, a, b, c = struct.unpack_from('<IIII', u, p)
        if (c & 0x3f) == 0x24 and ((c >> 8) & 15) == 9 and ((c >> 12) & 15) == 9:
            return u[:p] + b''.join(hh_records(page, {'b': b, 'c': c})) + u[p:]
        if n == 0:
            break
        p += n * 4
    return None


def ie_repack(raw, newdata):
    e, end = ie.entries(raw)
    assert len(e) == 1
    x = e[0]
    name = x['name'].encode()
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    c = comp.compress(newdata) + comp.flush()
    crc = zlib.crc32(newdata)
    lh = bytearray(x['hdr'])
    struct.pack_into('<III', lh, 14, crc, len(c), len(newdata))
    cd = bytearray(raw[end:])
    assert cd[:4] == b'PK\x01\x02'
    struct.pack_into('<III', cd, 16, crc, len(c), len(newdata))
    cdlen = 46 + struct.unpack_from('<HHH', cd, 28)[0] + struct.unpack_from('<HHH', cd, 28)[1] + struct.unpack_from('<HHH', cd, 28)[2]
    eocd = cd[cdlen:]
    assert eocd[:4] == b'PK\x05\x06'
    struct.pack_into('<I', eocd, 16, len(lh) + len(c))
    return bytes(lh) + c + bytes(cd[:cdlen]) + bytes(eocd)


# ------------------------------------------------------------------ ISO
def iso_dir_records(f):
    """경로 -> (레코드 위치(바이트), lba, size)"""
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    root = pvd[156:156 + 34]
    out = {}

    def walk(lba, size, path):
        f.seek(lba * SEC)
        d = f.read(size)
        p = 0
        while p < len(d):
            n = d[p]
            if n == 0:
                p = (p // SEC + 1) * SEC
                continue
            elba, esz = struct.unpack_from('<I', d, p + 2)[0], struct.unpack_from('<I', d, p + 10)[0]
            fl = d[p + 25]
            nm = d[p + 33:p + 33 + d[p + 32]]
            if nm not in (b'\0', b'\1'):
                name = nm.decode('latin1').split(';')[0]
                full = path + '/' + name
                if fl & 2:
                    walk(elba, esz, full)
                else:
                    out[full.upper()] = (lba * SEC + p, elba, esz)
            p += n
    walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0], '')
    return out


def both32(v):
    return struct.pack('<I', v) + struct.pack('>I', v)


def build_iso(files):
    """files: {'/LVL/X.RTX': bytes}"""
    shutil.copyfile(SRC_ISO, OUT_ISO)
    with open(OUT_ISO, 'r+b') as f:
        recs = iso_dir_records(f)
        f.seek(0, 2)
        total = f.tell() // SEC
        u = udf.UDF(f)
        for path, data in sorted(files.items()):
            pos, lba, size = recs[path.upper()]
            if (len(data) + SEC - 1) // SEC <= (size + SEC - 1) // SEC:
                nl = lba
            else:
                nl = total
                total += (len(data) + SEC - 1) // SEC
            f.seek(nl * SEC)
            f.write(data + b'\0' * ((-len(data)) % SEC))
            f.seek(pos + 2)
            f.write(both32(nl) + both32(len(data)))
            u.set_file(path, nl, len(data))
        f.truncate(total * SEC)
        # PVD 볼륨 크기
        f.seek(16 * SEC + 80)
        f.write(both32(total))
        u.grow(total)


# ------------------------------------------------------------------ main
def main():
    ko = load_ko()
    cnt = collections.Counter()
    first = {}
    for off in sorted(ko):
        for c in tokens(ko[off]):
            if is_hangul(c):
                cnt[c] += 1
                first.setdefault(c, off)
    chars = sorted(cnt, key=lambda c: (-cnt[c], first[c]))
    cap = kfont.COLS * ((512 - Y0) // kfont.PITCH)
    print('번역 %d개, 한글 %d자 / %d' % (len(ko), len(chars), cap))
    assert len(chars) <= cap and len(chars) <= NLEAD * 96
    code_map = {c: i for i, c in enumerate(chars)}
    page = kfont.build_page(chars, Y0)
    os.makedirs(os.path.join(ROOT, 'work'), exist_ok=True)
    kfont.preview(page).save(os.path.join(ROOT, 'work', 'kpage.png'))

    import pycdlib
    iso = pycdlib.PyCdlib()
    iso.open(SRC_ISO)
    import io

    def get(p):
        b = io.BytesIO()
        iso.get_file_from_iso_fp(b, iso_path=p + ';1')
        return b.getvalue()
    files = {}
    mode = os.environ.get('DD_MODE', 'all')     # 분할 시험용: all / elf / rtx / repack
    elf = get('/SCUS_971.77')
    if mode in ('all', 'elf'):
        files['/SCUS_971.77'] = build_elf(elf, ko, code_map)
    rtxs = ['/SHELL/UI.RTX'] + ['/LVL/' + c.file_identifier().decode().split(';')[0]
                                for c in iso.list_children(iso_path='/LVL') if c.file_identifier().decode().endswith('.RTX;1')]
    for p in rtxs if mode != 'elf' else []:
        raw = get(p)
        e, _ = ie.entries(raw)
        u = e[0]['data'] if mode == 'repack' else patch_rtx(e[0]['data'], page)
        files[p] = ie_repack(raw, u)
    nlb = 0
    for c in iso.list_children(iso_path='/LOADBAR') if mode != 'elf' else []:
        nm = c.file_identifier().decode()
        if nm.endswith('.RTX;1'):
            p = '/LOADBAR/' + nm.split(';')[0]
            u = patch_loadbar(get(p), page)
            if u:
                files[p] = u
                nlb += 1
    iso.close()
    print('RTX 수정', len(rtxs), '+ LOADBAR', nlb)
    build_iso(files)
    print('완료:', OUT_ISO)


if __name__ == '__main__':
    main()
