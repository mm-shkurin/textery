import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROVIDER_DIR = os.path.dirname(_TESTS_DIR)
_ADAPTERS_DIR = os.path.dirname(_PROVIDER_DIR)
_BACKEND_DIR = os.path.dirname(_ADAPTERS_DIR)
_PROVIDER_SRC = os.path.join(_PROVIDER_DIR, "src")
_DOMAIN_SRC = os.path.join(_BACKEND_DIR, "domain", "src")
_USECASE_SRC = os.path.join(_BACKEND_DIR, "usecase", "src")

sys.path.insert(0, _PROVIDER_SRC)
sys.path.insert(0, _DOMAIN_SRC)
sys.path.insert(0, _USECASE_SRC)
