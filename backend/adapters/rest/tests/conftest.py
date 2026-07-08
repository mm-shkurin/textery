import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_REST_DIR = os.path.dirname(_TESTS_DIR)
_ADAPTERS_DIR = os.path.dirname(_REST_DIR)
_BACKEND_DIR = os.path.dirname(_ADAPTERS_DIR)
_REST_SRC = os.path.join(_REST_DIR, "src")
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")

sys.path.insert(0, _REST_SRC)
sys.path.insert(0, _DOMAIN_SRC)
