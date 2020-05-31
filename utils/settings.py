from os.path import abspath, dirname, join
import os

Domain = "Aminer"

PROJ_DIR = join(abspath(dirname(__file__)), '..')

DATA_DIR = join(PROJ_DIR, 'data', Domain)
OUT_DIR = join(PROJ_DIR, 'out', Domain)
PIC_DIR = join(PROJ_DIR, 'pic', Domain)
EMB_DATA_DIR = join(DATA_DIR, 'emb')
GLOBAL_DATA_DIR = join(DATA_DIR, 'global')
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(EMB_DATA_DIR, exist_ok=True)


