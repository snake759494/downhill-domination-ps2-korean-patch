"""ELF 문자열 + 참조(데이터 포인터/코드 lui-addiu) 수집"""
import struct,re,json,sys
sys.path.insert(0,'tools');import elf
D=elf.D;B=elf.BASE
LO,HI=0x164d00,0x194cf0   # .data ~ .sdata (file offsets)
# 1) data pointers: any aligned u32 in .data/.rodata/.sdata pointing into [LO,HI)
ptrs={}
for o in range(LO,HI,4):
    v=struct.unpack_from('<I',D,o)[0]-B
    if LO<=v<HI: ptrs.setdefault(v,[]).append(o)
# 2) code refs (lui/addiu pairs) across .text
code={}
regs={}
for a in range(0x10a000,0x263bc0,4):
    w=elf.u32(a);op=w>>26
    if op==0x0f: regs[(w>>16)&31]=(w&0xffff,a)
    elif op==0x09:
        rs=(w>>21)&31
        if rs in regs and a-regs[rs][1]<0x100:
            v=((regs[rs][0]<<16)+((w&0xffff)^0x8000)-0x8000)-B
            if LO<=v<HI: code.setdefault(v,[]).append((regs[rs][1],a))
# 3) strings
out=[]
for m in re.finditer(rb'[\x09\x0a\x20-\x7e\x80-\xff]{1,}\x00',D[LO:HI]):
    s=m.start()+LO;t=m.group()[:-1]
    # allow sub-string starts (pointers into middle)
    starts=[s]+[k for k in range(s+1,s+len(t)) if k in ptrs or k in code]
    for st in starts:
        txt=D[st:s+len(t)]
        if not txt: continue
        out.append(dict(off=st,end=s+len(t),text=txt.decode('latin1'),ptr=ptrs.get(st,[]),code=[list(x) for x in code.get(st,[])]))
json.dump(out,open('work/strings_all.json','w'),indent=0)
print(len(out),sum(1 for x in out if x['ptr'] or x['code']))
