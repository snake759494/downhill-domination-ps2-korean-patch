import struct,capstone
ELF='work/ext/SCUS_971.77'
D=open(ELF,'rb').read()
BASE=0x109000  # vaddr = off + BASE
def u32(a): return struct.unpack_from('<I',D,a-BASE)[0]
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS64|capstone.CS_MODE_LITTLE_ENDIAN)
def dis(a,n=40):
    out=[]
    for i in range(n):
        w=D[a-BASE+4*i:a-BASE+4*i+4]
        l=list(md.disasm(w,a+4*i))
        out.append('%08x: %08x  %s'%(a+4*i,struct.unpack('<I',w)[0],(l[0].mnemonic+' '+l[0].op_str) if l else '??'))
    return '\n'.join(out)
def xrefs(target,lo=0x10a000,hi=0x263bc0):
    """find lui/addiu(or ori/lw) pairs forming target"""
    res=[];hi16=(target+0x8000)>>16;lo16=target&0xffff
    regs={}
    for a in range(lo,hi,4):
        w=u32(a);op=w>>26
        if op==0x0f: regs[(w>>16)&31]=(w&0xffff,a)
        elif op in(0x09,0x23,0x0d,0x21,0x24,0x25,0x2b,0x28,0x29,0x20) :
            rs=(w>>21)&31;imm=w&0xffff
            if rs in regs and regs[rs][0]==hi16 and imm==lo16 and a-regs[rs][1]<0x80: res.append(a)
            elif rs in regs and op==0x0d and regs[rs][0]==target>>16 and imm==lo16: res.append(a)
    return res
def funcstart(a):
    while a>0x10a000:
        w=u32(a)
        if (w&0xffff0000)==0x27bd0000 and (w&0x8000): return a
        a-=4
if __name__=='__main__':
    import sys
    c=sys.argv[1]
    if c=='dis': print(dis(int(sys.argv[2],16),int(sys.argv[3]) if len(sys.argv)>3 else 40))
    elif c=='x':
        t=int(sys.argv[2],16)
        for r in xrefs(t): print(hex(r),'func',hex(funcstart(r) or 0))
    elif c=='xs':  # xref by file offset of string
        t=int(sys.argv[2],16)+BASE
        for r in xrefs(t): print(hex(r),'func',hex(funcstart(r) or 0))
