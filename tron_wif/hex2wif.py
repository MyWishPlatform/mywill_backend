import sys

from Naked.toolshed.shell import execute_js, muterun_js


def hex2tronwif(hexstr):
    response = muterun_js('hextob58.js', hexstr)
    if response.exitcode == 0:
        return response.stdout.decode().strip()
    else:
        sys.stderr.write(response.stderr.decode().strip())
