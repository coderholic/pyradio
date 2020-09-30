import sys
import glob
from os.path import sep, basename

def show_python_dirs():
    import site
    for n in site.getsitepackages():
         print(n)
    exit(0)

pdir = False;
try:
    if sys.argv[1] == 'python':
        pdir = True
except:
    pass

if pdir:
    show_python_dirs()

try:
    with open('dirs', 'r') as f:
        lines=f.read()
except:
        show_python_dirs()

dirs = []
dirs = lines.split('\n')
if dirs:
    py_dirs = []
    for a_dir in dirs:
        if a_dir:
            pydirs = glob.glob(a_dir + sep + 'pyradio*egg')
            if pydirs:
                with open("pyremove.bat", "a") as f:
                    f.write('echo Looking for python installed files...\n')
                    for a_dir in pydirs:
                        f.write('echo ** Removing "{}" ... done \n'.format(basename(a_dir)))
                        f.write('RD /S /Q "{}"\n'.format(a_dir))
