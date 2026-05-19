import time
import json
import os

TTL = {
    "atual":   30 * 60,
    "diaria":  6 * 60 * 60,
    "horaria": 60 * 60,
}

CACHE_FILE = "output/cache.json"
_memoria = {}


def _carregar():
    global _memoria
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                _memoria = json.load(f)
        except Exception:
            _memoria = {}


def _salvar():
    os.makedirs("output", exist_ok=True)
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(_memoria, f)
    except Exception:
        pass


def _chave(lat: float, lon: float, tipo: str) -> str:
    return f"{tipo}:{round(lat, 2)}:{round(lon, 2)}"


def get(lat: float, lon: float, tipo: str):
    chave = _chave(lat, lon, tipo)
    entrada = _memoria.get(chave)

    if not entrada:
        return None

    idade = time.time() - entrada["ts"]
    if idade > TTL[tipo]:
        del _memoria[chave]
        return None

    minutos = int((TTL[tipo] - idade) / 60)
    print(f"  ✅ Cache HIT [{tipo}] ({minutos}min restantes)")
    return entrada["dados"]


def set(lat: float, lon: float, tipo: str, dados: dict):
    chave = _chave(lat, lon, tipo)
    _memoria[chave] = {"dados": dados, "ts": time.time()}
    _salvar()
    print(f"  💾 Cache SET [{tipo}]")


def stats() -> dict:
    return {
        "total_entradas": len(_memoria),
        "cache_file": CACHE_FILE,
        "ttl_atual_min": TTL["atual"] // 60,
        "ttl_diaria_h": TTL["diaria"] // 3600,
        "ttl_horaria_h": TTL["horaria"] // 3600,
    }


_carregar()
