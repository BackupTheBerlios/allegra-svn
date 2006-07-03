import sys

sys.stdout.write ('stdout: start\n')
while True:
        line = sys.stdin.readline ()
        if line == '\n':
                break
        
        sys.stdout.write (line)
sys.stderr.write ('stderr: ...\n')
sys.stdout.write ('stdout: stop\n')

sys.exit (0)