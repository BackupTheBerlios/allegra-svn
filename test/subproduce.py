# a script to be started as a subprocess

import sys

sys.stdout.write ('stdout: start\n')
sys.stderr.write ('stderr: ...\n')
sys.stdout.write ('stdout: stop\n')

sys.exit (0)