import os 

base = "../../../doc/manual/insns/"
li = os.listdir(base)
print(li)
for i in li:
    f = open(base+i)
    d = f.readlines()
    f.close()
    for j in d:
        if j.find("begin{inst") > 0:
            val = j.strip().split("}{")
            name = val[1]
            descr = val[2][:-1]
        if j.find("\\assembly") > 0:
            val = j.strip().split("}")
            reg = val[1].strip()
    print(name,' ', reg , ";" ,descr)
