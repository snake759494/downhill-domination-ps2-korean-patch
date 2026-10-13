# IE\3\4 = ZIP local file header with altered magic; method 8 = raw deflate
import struct,zlib,sys,os
def entries(d):
    p=0;out=[]
    while p+30<=len(d) and d[p:p+4]==b'IE\x03\x04':
        ver,fl,meth,tm,dt,crc,cs,us,nl,xl=struct.unpack_from('<HHHHHIIIHH',d,p+4)
        name=d[p+30:p+30+nl].decode('latin1');q=p+30+nl+xl
        raw=d[q:q+cs]
        data=zlib.decompress(raw,-15) if meth==8 else raw
        out.append(dict(name=name,off=p,meth=meth,cs=cs,us=us,crc=crc,data=data,hdr=d[p:q]))
        p=q+cs
    return out,p
def pack(name,data,tmdt=(0x90ca,0x2ec8),level=9):
    c=zlib.compressobj(level,zlib.DEFLATED,-15);raw=c.compress(data)+c.flush()
    h=b'IE\x03\x04'+struct.pack('<HHHHHIIIHH',0x14,0,8,0,0,zlib.crc32(data),len(raw),len(data),len(name),0)+name.encode()
    return h+raw
if __name__=='__main__':
    d=open(sys.argv[1],'rb').read();e,end=entries(d)
    print(len(d),end,[(x['name'],x['cs'],x['us']) for x in e])
    if len(sys.argv)>2:
        for x in e: open(os.path.join(sys.argv[2],x['name']),'wb').write(x['data'])
