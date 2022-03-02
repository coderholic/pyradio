import site
import subprocess
from os import path

paths = site.getsitepackages()

ph = ['', '']
ex = ['', '']
for p in paths:
    if 'site-packages' in p:
        ph[1] = p
        ex[1] = 'RD /Q /S "{}\\pyradio*.egg"'.format(p)
    else:
        ph[0] = p
        ex[0] = 'DEL "{}\\Scripts\\pyradio.exe"'.format(p)
failed = False
for i, x in enumerate(ex):
    print('Executing: {}'.format(x), end='', flush=True)
    subprocess.call(x, shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    if path.exists(ph[i]):
        print('  ...  Failed')
        failed = True
    else:
        print('  ...  OK')

if failed:
    print('\nPlease run this in a console opened with "Run as Administrator"')
