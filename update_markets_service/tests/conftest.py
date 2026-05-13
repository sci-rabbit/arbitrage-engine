"""
Env vars must be set before any module that triggers `settings = Settings()`.
"""
import os

os.environ.setdefault("DB__USER", "test")
os.environ.setdefault("DB__PASSWORD", "test")
os.environ.setdefault("DB__HOST", "localhost")
os.environ.setdefault("DB__PORT", "5432")
os.environ.setdefault("DB__NAME", "test")
os.environ.setdefault("KALSHI__PROXY_URL", "")
os.environ.setdefault("POLYMARKET__PROXY_URL", "")
os.environ.setdefault("PREDICT_FUN__API_KEY", "test_key")
os.environ.setdefault("PREDICT_FUN__PROXY_URL", "")
