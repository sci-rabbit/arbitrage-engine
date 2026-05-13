import ast

import numpy as np


def parse_embedding(emb_str):
    if isinstance(emb_str, np.ndarray):
        return emb_str
    if isinstance(emb_str, str):
        return np.array(ast.literal_eval(emb_str), dtype=np.float32)
    return np.array(emb_str, dtype=np.float32)

def cosine(a, b) -> float:
    if a is None or b is None:
        return 0.0
    a = parse_embedding(a)
    b = parse_embedding(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))