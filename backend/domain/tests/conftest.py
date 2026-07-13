import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_DOMAIN_DIR = os.path.dirname(_TESTS_DIR)
_DOMAIN_SRC = os.path.join(_DOMAIN_DIR, "src")

sys.path.insert(0, _DOMAIN_SRC)
