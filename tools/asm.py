"""작은 MIPS(R5900) 어셈블러 — 패치 코드용.

한 줄에 명령 하나, 라벨은 'name:'. 지연 슬롯은 직접 채운다(자동 nop 없음).
숫자는 0x.. / 10진 / 'lo(sym)' 'hi(sym)'(addiu 짝, 부호 보정) 지원.
"""
import re
import struct

REGS = {n: i for i, n in enumerate(
    'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}
REGS['s8'] = 30

R3 = {'addu': 0x21, 'subu': 0x23, 'and': 0x24, 'or': 0x25, 'xor': 0x26, 'nor': 0x27,
      'slt': 0x2a, 'sltu': 0x2b, 'daddu': 0x2d, 'dsubu': 0x2f}
SH = {'sll': 0, 'srl': 2, 'sra': 3, 'dsll': 0x38, 'dsrl': 0x3a, 'dsra': 0x3b,
      'dsll32': 0x3c, 'dsrl32': 0x3e, 'dsra32': 0x3f}
SHV = {'sllv': 4, 'srlv': 6, 'srav': 7, 'dsllv': 0x14, 'dsrlv': 0x16}
IMM = {'addiu': 9, 'slti': 10, 'sltiu': 11, 'andi': 12, 'ori': 13, 'xori': 14, 'daddiu': 25}
MEM = {'lb': 0x20, 'lh': 0x21, 'lw': 0x23, 'lbu': 0x24, 'lhu': 0x25, 'sb': 0x28, 'sh': 0x29,
       'sw': 0x2b, 'ld': 0x37, 'sd': 0x3f}
BR2 = {'beq': 4, 'bne': 5}
BR1 = {'blez': (6, 0), 'bgtz': (7, 0), 'bltz': (1, 0), 'bgez': (1, 1)}


def reg(s):
    s = s.strip().lstrip('$')
    return REGS[s]


class Asm:
    def __init__(self, base, syms=None):
        self.base = base
        self.syms = dict(syms or {})

    def num(self, s):
        s = s.strip()
        m = re.fullmatch(r'(lo|hi)\((.+)\)', s)
        if m:
            v = self.num(m.group(2))
            return (v & 0xffff) if m.group(1) == 'lo' else ((v + 0x8000) >> 16) & 0xffff
        if s in self.syms:
            return self.syms[s]
        return int(eval(s, {}, dict(self.syms)))

    def assemble(self, src):
        lines = []
        for raw in src.splitlines():
            l = raw.split('#')[0].strip()
            if not l:
                continue
            while ':' in l and re.match(r'^[A-Za-z_]\w*:', l):
                name, l = l.split(':', 1)
                self.syms[name] = self.base + 4 * len(lines)
                l = l.strip()
            if l:
                for x in self.expand(l):
                    lines.append(x)
        out = bytearray()
        for i, l in enumerate(lines):
            out += struct.pack('<I', self.enc(l, self.base + 4 * i))
        return bytes(out)

    def expand(self, l):
        op, _, rest = l.partition(' ')
        a = [x.strip() for x in rest.split(',')] if rest else []
        if op == 'la':      # la rd, sym  -> lui + addiu
            return [f'lui {a[0]}, hi({a[1]})', f'addiu {a[0]}, {a[0]}, lo({a[1]})']
        if op == 'li32':
            return [f'lui {a[0]}, (({a[1]})>>16)&0xffff', f'ori {a[0]}, {a[0]}, ({a[1]})&0xffff']
        return [l]

    def enc(self, l, pc):
        op, _, rest = l.partition(' ')
        a = [x.strip() for x in rest.split(',')] if rest else []
        if op == 'nop':
            return 0
        if op == 'move':
            return (reg(a[1]) << 21) | (reg(a[0]) << 11) | 0x2d
        if op == 'li':
            v = self.num(a[1]) & 0xffff
            return (9 << 26) | (reg(a[0]) << 16) | v
        if op in R3:
            return (reg(a[1]) << 21) | (reg(a[2]) << 16) | (reg(a[0]) << 11) | R3[op]
        if op in SH:
            return (reg(a[1]) << 16) | (reg(a[0]) << 11) | ((self.num(a[2]) & 31) << 6) | SH[op]
        if op in SHV:
            return (reg(a[2]) << 21) | (reg(a[1]) << 16) | (reg(a[0]) << 11) | SHV[op]
        if op in IMM:
            return (IMM[op] << 26) | (reg(a[1]) << 21) | (reg(a[0]) << 16) | (self.num(a[2]) & 0xffff)
        if op == 'lui':
            return (15 << 26) | (reg(a[0]) << 16) | (self.num(a[1]) & 0xffff)
        if op in MEM:
            m = re.fullmatch(r'(.*)\((.+)\)', a[1])
            off = self.num(m.group(1)) if m.group(1).strip() else 0
            return (MEM[op] << 26) | (reg(m.group(2)) << 21) | (reg(a[0]) << 16) | (off & 0xffff)
        if op in BR2:
            t = self.num(a[2])
            d = (t - pc - 4) >> 2
            assert -0x8000 <= d < 0x8000
            return (BR2[op] << 26) | (reg(a[0]) << 21) | (reg(a[1]) << 16) | (d & 0xffff)
        if op == 'b':
            d = (self.num(a[0]) - pc - 4) >> 2
            return (4 << 26) | (d & 0xffff)
        if op in BR1:
            o, rt = BR1[op]
            d = (self.num(a[1]) - pc - 4) >> 2
            return (o << 26) | (reg(a[0]) << 21) | (rt << 16) | (d & 0xffff)
        if op in ('j', 'jal'):
            t = self.num(a[0])
            assert (t & 0xf0000000) == (pc & 0xf0000000)
            return ((2 if op == 'j' else 3) << 26) | ((t >> 2) & 0x3ffffff)
        if op == 'jr':
            return (reg(a[0]) << 21) | 8
        if op == 'jalr':
            return (reg(a[0]) << 21) | (31 << 11) | 9
        if op == 'mflo':
            return (reg(a[0]) << 11) | 0x12
        if op == 'mult':
            return (reg(a[0]) << 21) | (reg(a[1]) << 16) | 0x18
        if op == 'mul':     # R5900 3-operand mult (rd = rs*rt)
            return (reg(a[1]) << 21) | (reg(a[2]) << 16) | (reg(a[0]) << 11) | 0x18
        raise ValueError('unknown op: ' + l)
