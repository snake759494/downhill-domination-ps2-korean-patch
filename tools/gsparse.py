import struct,sys
def packets(d):
    hs=struct.unpack_from('<I',d,4)[0];h=d[8:8+hs]
    ss=struct.unpack_from('<I',h,4)[0]
    p=8+hs+ss+8192
    while p<len(d):
        t=d[p];p+=1
        if t==0:
            path=d[p];sz=struct.unpack_from('<I',d,p+1)[0];p+=5
            yield ('T',path,d[p:p+sz]);p+=sz
        elif t==1: yield ('V',d[p]);p+=1
        elif t==2: p+=4
        elif t==3: yield ('R',d[p:p+8192]);p+=8192
        else: raise Exception('bad %d at %x'%(t,p))
REGN={0:'PRIM',1:'RGBAQ',2:'ST',3:'UV',4:'XYZF2',5:'XYZ2',6:'TEX0_1',7:'TEX0_2',0xe:'AD',0xf:'NOP'}
def giftags(data):
    p=0
    while p+16<=len(data):
        lo,hi=struct.unpack_from('<QQ',data,p);p+=16
        nloop=lo&0x7fff;eop=(lo>>15)&1;pre=(lo>>46)&1;prim=(lo>>47)&0x7ff;flg=(lo>>58)&3;nreg=(lo>>60)&0xf or 16
        regs=[(hi>>(4*i))&0xf for i in range(nreg)]
        if flg==0:
            items=[]
            for _ in range(nloop):
                for r in regs:
                    v=struct.unpack_from('<QQ',data,p);p+=16
                    if r==0xe: items.append(('A%02x'%(v[1]&0xff),v[0]))
                    else: items.append((r,v))
            yield ('PACKED',pre,prim,items)
        elif flg==1:
            items=[]
            for _ in range(nloop):
                for r in regs:
                    v=struct.unpack_from('<Q',data,p)[0];p+=8
                    items.append((r,v))
            if (nloop*nreg)%2: p+=8
            yield ('REGLIST',pre,prim,items)
        else:
            yield ('IMAGE',nloop*16,None,None);p+=nloop*16
