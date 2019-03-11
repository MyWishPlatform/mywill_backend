import sys
import os

from Naked.toolshed.shell import execute_js, muterun_js


def hex2tronwif(hexstr):
    spath = os.path.dirname(os.path.abspath(__file__))
    sname = 'hextob58.js'
    js_path = os.path.join(spath, sname)

    response = muterun_js(js_path, hexstr)
    if response.exitcode == 0:
        return response.stdout.decode().strip()
    else:
        sys.stderr.write(response.stderr.decode().strip())
