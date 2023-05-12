import time
import os

print("STARTING")

print("BEFORE start.fix")
if not os.path.isfile('start.fix'):
    raise RuntimeError("start.fix not present")
print("AFTER start.fix")

print("BEFORE error.fix")
if not os.path.isfile('error.fix'):
    raise RuntimeError('error.fix not present')
print("AFTER error.fix")

print("BEFORE generic.fix")
while not os.path.isfile('generic.fix'):
    print('waiting for generic.fix...')
    time.sleep(1)
print("AFTER generic.fix")

print("BEFORE blocking.fix")
if not os.path.isfile('blocking.fix'):
    while True:
        time.sleep(0.5)
        print("blocking...")
print("AFTER blocking.fix")

print("BEFORE timeout.fix")
for i in range(0, 9):
    time.sleep(1)
print("AFTER timeout.fix")

print("trigger ERROR fix")

print("BEFORE removing fix files")
here = os.listdir()
for file in here:
    if file.endswith('.fix'):
        os.remove(file)
print("AFTER removing fix files")

print("READY FOR INSPECTION")

print("READY FOR TERMINAL")

print("FINISHED")
