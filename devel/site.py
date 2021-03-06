import site
import sys
if len(sys.argv) == 1:
    for n in site.getsitepackages():
         print(n)
    p = site.getusersitepackages()
    if isinstance(p, str):
        print(p)
    else:
        for n in p:
            print(n)
else:
    from os import environ
    import glob
    alldirs = environ['PATH'].split(';')
    for n in alldirs:
        if 'python' in n or 'Python' in n:
            f = glob.glob(n+'pyradio*.*')
            if f:
                for exe in f:
                    print('DEL "' + exe + '"')
