import requests
import os
from dotenv import load_dotenv
import cache as _cache

load_dotenv()

API_KEY = os.getenv("GOOGLE_WEATHER_API_KEY")
BASE_URL = "https://weather.googleapis.com/v1"


def _get(url: str, params: dict) -> dict:
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_condicoes_atuais(lat: float, lon: float) -> dict:
    dados = _cache.get(lat, lon, "atual")
    if dados:
        return dados

    print(f"  🌐 API CALL [atual] lat={lat} lon={lon}")
    dados = _get(
        f"{BASE_URL}/currentConditions:lookup",
        {
            "key": API_KEY,
            "location.latitude": lat,
            "location.longitude": lon,
            "unitsSystem": "METRIC"
        }
    )
    _cache.set(lat, lon, "atual", dados)
    return dados


def get_previsao_diaria(lat: float, lon: float, dias: int = 7) -> dict:
    dados = _cache.get(lat, lon, "diaria")
    if dados:
        return dados

    print(f"  🌐 API CALL [diaria] lat={lat} lon={lon}")
    dados = _get(
        f"{BASE_URL}/forecast/days:lookup",
        {
            "key": API_KEY,
            "location.latitude": lat,
            "location.longitude": lon,
            "days": dias,
            "unitsSystem": "METRIC"
        }
    )
    _cache.set(lat, lon, "diaria", dados)
    return dados


def get_previsao_horaria(lat: float, lon: float, horas: int = 48) -> dict:
    dados = _cache.get(lat, lon, "horaria")
    if dados:
        return dados

    print(f"  🌐 API CALL [horaria] lat={lat} lon={lon}")
    dados = _get(
        f"{BASE_URL}/forecast/hours:lookup",
        {
            "key": API_KEY,
            "location.latitude": lat,
            "location.longitude": lon,
            "hours": horas,
            "unitsSystem": "METRIC"
        }
    )
    _cache.set(lat, lon, "horaria", dados)
    return dados
