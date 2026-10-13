import struct
def entries(d):
    p=0;out=[]
    while p+16<=len(d):
        n,a,b,c=struct.unpack_from('<IIII',d,p)
        if n==0: break
        out.append(dict(off=p,words=n,a=a,b=b,c=c,data=d[p+16:p+n*4]))
        p+=n*4
    return out,p
if __name__=='__main__':
    import sys
    d=open(sys.argv[1],'rb').read();e,p=entries(d)
    print(len(d),hex(p),len(e))
    for x in e: print(hex(x['off']),hex(x['words']*4),hex(x['a']),hex(x['b']),hex(x['c']))
