"""
Set env vars before any module that triggers settings = Settings().
Exclude legacy script-style files from pytest collection.
"""
import os

collect_ignore = ["test_similarity.py", "test.py"]

os.environ.setdefault("DB__USER", "test")
os.environ.setdefault("DB__PASSWORD", "test")
os.environ.setdefault("DB__HOST", "localhost")
os.environ.setdefault("DB__PORT", "5432")
os.environ.setdefault("DB__NAME", "test")
os.environ.setdefault("REDIS__HOST", "localhost")
os.environ.setdefault("REDIS__PORT", "6379")
os.environ.setdefault("REDIS__PASSWORD", "test")
os.environ.setdefault("REDIS__DB", "0")
os.environ.setdefault("JWT__SECRET_KEY", "test_secret_key_for_testing_only")
