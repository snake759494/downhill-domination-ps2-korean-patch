import struct
def records(f):
    f.seek(16*2048);pvd=f.read(2048)
    rl,rs=struct.unpack_from('<I',pvd,156+2)[0],struct.unpack_from('<I',pvd,156+10)[0]
    f.seek(rl*2048);d=f.read(rs);out={};p=0
    while p<len(d):
        n=d[p]
        if n==0: p=(p//2048+1)*2048;continue
        lba,sz=struct.unpack_from('<I',d,p+2)[0],struct.unpack_from('<I',d,p+10)[0]
        nm=d[p+33:p+33+d[p+32]].decode('latin1').split(';')[0]
        if nm not in('\x00','\x01'): out[nm]=(lba,sz,rl*2048+p)
        p+=n
    return out
if __name__=='__main__':
    for k,v in sorted(records(open('Darkwatch (USA).iso','rb')).items(),key=lambda x:x[1]): print(k,v)
