# Импортируем все лоадеры, чтобы декораторы @add_loader выполнились
# from core.load_markets.loaders import load_polymarket  # noqa: F401
from core.load_markets.loaders import load_kalshi, load_polymarket, load_predict_fun  # noqa: F401