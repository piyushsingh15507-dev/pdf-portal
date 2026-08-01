import os
import sys

folder = r'C:\Users\HP\Downloads\SciAstra_Backup_Tool (1)\Course_840821\Daily Class Recordings & Notes\Biology\Ch 1_ Cell _ The Unit Of Life\Lecture Recordings'
files = os.listdir(folder)

for f in sorted(files):
    sys.stdout.buffer.write((f + "\n").encode('utf-8'))
