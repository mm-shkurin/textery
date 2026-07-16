import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_SECURITY_DIR = os.path.dirname(_TESTS_DIR)
_ADAPTERS_DIR = os.path.dirname(_SECURITY_DIR)
_BACKEND_DIR = os.path.dirname(_ADAPTERS_DIR)
_SECURITY_SRC = os.path.join(_SECURITY_DIR, "src")
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")
_USECASE_SRC = os.path.join(_BACKEND_DIR, "usecase", "src")

sys.path.insert(0, _SECURITY_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)
