import re,sys
d=open(sys.argv[1],'rb').read()
pat=sys.argv[2].encode() if len(sys.argv)>2 else None
for m in re.finditer(rb'[\x20-\x7e\n]{6,}',d):
    s=m.group()
    if pat is None or re.search(pat,s,re.I): print(hex(m.start()),s.decode()[:200])
