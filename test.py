import fcntl
import os
import subprocess

p = subprocess.Popen(['./pianobar'], stdout=subprocess.PIPE, stdin=subprocess.PIPE)
fd = p.stdout.fileno()
fl = fcntl.fcntl(fd, fcntl.F_GETFL)
fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
