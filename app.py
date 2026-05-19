from flask import Flask, jsonify, render_template, request, session
from dotenv import load_dotenv
from weather_client import get_condicoes_atuais, get_previsao_diaria, get_previsao_horaria
from agro_analysis import (
    analisar_para_irrigacao,
    analisar_para_pulverizacao,
    analisar_geada,
    calcular_graus_dia
)
from config import FAZENDAS
import cache
import os
import json
import csv
import io

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "climaiagro-secret-2024")


# ─── PÁGINAS ────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ─── API FAZENDAS ─────────────────────────────────────────

@app.route("/api/fazendas", methods=["GET"])
def listar_fazendas():
    return jsonify(session.get("fazendas", []))


@app.route("/api/fazendas", methods=["POST"])
def adicionar_fazenda():
    data = request.get_json()
    try:
        lat = float(data.get("lat", ""))
        lon = float(data.get("lon", ""))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "erro": "Latitude e longitude devem ser números."})

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return jsonify({"ok": False, "erro": "Coordenadas fora do intervalo válido."})

    fazendas = session.get("fazendas", [])
    nova = {
        "id": len(fazendas),
        "nome": data.get("nome", "").strip() or f"Ponto {len(fazendas)+1}",
        "lat": lat,
        "lon": lon,
        "cultura": data.get("cultura", "soja"),
    }
    fazendas.append(nova)
    session["fazendas"] = fazendas
    session.modified = True
    return jsonify({"ok": True, "fazenda": nova})


@app.route("/api/fazendas/<int:fid>", methods=["DELETE"])
def remover_fazenda(fid):
    fazendas = session.get("fazendas", [])
    session["fazendas"] = [f for f in fazendas if f["id"] != fid]
    session.modified = True
    return jsonify({"ok": True})


@app.route("/api/fazendas/upload", methods=["POST"])
def upload_fazendas():
    if "arquivo" not in request.files:
        return jsonify({"ok": False, "erro": "Nenhum arquivo enviado."})

    arquivo = request.files["arquivo"]
    nome = arquivo.filename.lower()

    try:
        if nome.endswith(".csv"):
            fazendas = _parsear_csv(arquivo)
        elif nome.endswith(".geojson") or nome.endswith(".json"):
            fazendas = _parsear_geojson(arquivo)
        else:
            return jsonify({"ok": False, "erro": "Formato não suportado. Use CSV ou GeoJSON."})

        if not fazendas:
            return jsonify({"ok": False, "erro": "Nenhuma fazenda encontrada no arquivo."})

        session["fazendas"] = fazendas
        return jsonify({"ok": True, "total": len(fazendas), "fazendas": fazendas})

    except Exception as e:
        return jsonify({"ok": False, "erro": f"Erro ao processar arquivo: {str(e)}"})


@app.route("/api/fazendas/limpar", methods=["POST"])
def limpar_fazendas():
    session.pop("fazendas", None)
    return jsonify({"ok": True})


def _parsear_csv(arquivo) -> list:
    """
    Aceita CSV com colunas: nome, lat, lon, cultura
    A ordem das colunas não importa, mas os nomes sim.
    """
    texto = arquivo.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(texto))

    # normaliza nomes de colunas (remove espaços, lowercase)
    reader.fieldnames = [c.strip().lower() for c in reader.fieldnames]

    fazendas = []
    for i, row in enumerate(reader):
        row = {k.strip().lower(): v.strip() for k, v in row.items()}
        fazendas.append({
            "id": i,
            "nome": row.get("nome") or row.get("name") or f"Fazenda {i+1}",
            "lat": float(row.get("lat") or row.get("latitude")),
            "lon": float(row.get("lon") or row.get("longitude") or row.get("lng")),
            "cultura": row.get("cultura") or row.get("culture") or row.get("crop") or "soja",
        })
    return fazendas


def _parsear_geojson(arquivo) -> list:
    """
    Aceita GeoJSON FeatureCollection com Point features.
    Propriedades esperadas: nome, lat, lon (ou extrai da geometry), cultura
    """
    dados = json.loads(arquivo.read().decode("utf-8"))
    features = dados.get("features", [])

    fazendas = []
    for i, feat in enumerate(features):
        props = {k.lower(): v for k, v in feat.get("properties", {}).items()}
        geom = feat.get("geometry", {})

        if geom.get("type") == "Point":
            lon, lat = geom["coordinates"][0], geom["coordinates"][1]
        else:
            lat = float(props.get("lat") or props.get("latitude", 0))
            lon = float(props.get("lon") or props.get("longitude") or props.get("lng", 0))

        fazendas.append({
            "id": i,
            "nome": props.get("nome") or props.get("name") or f"Fazenda {i+1}",
            "lat": lat,
            "lon": lon,
            "cultura": props.get("cultura") or props.get("culture") or props.get("crop") or "soja",
        })
    return fazendas


# ─── API CLIMA ────────────────────────────────────────────

@app.route("/api/recomendacao")
def recomendacao():
    lat     = float(request.args.get("lat"))
    lon     = float(request.args.get("lon"))
    cultura = request.args.get("cultura", "soja")

    try:
        atual      = get_condicoes_atuais(lat, lon)
        previsao_d = get_previsao_diaria(lat, lon, dias=7)
        previsao_h = get_previsao_horaria(lat, lon, horas=48)

        temp     = atual.get("temperature", {}).get("degrees", 0)
        umidade  = atual.get("relativeHumidity", 0)
        vento    = atual.get("wind", {}).get("speed", {}).get("value", 0)
        condicao = atual.get("weatherCondition", {}).get("description", {}).get("text", "")

        dias = []
        for d in previsao_d.get("forecastDays", []):
            dias.append({
                "data":     d.get("interval", {}).get("startTime", "")[:10],
                "temp_max": d.get("maxTemperature", {}).get("degrees", 0),
                "temp_min": d.get("minTemperature", {}).get("degrees", 0),
                "chuva":    d.get("precipitation", {}).get("probability", {}).get("percent", 0),
            })

        janelas = []
        for h in previsao_h.get("forecastHours", []):
            v_vento = h.get("wind", {}).get("speed", {}).get("value", 99)
            v_chuva = h.get("precipitation", {}).get("probability", {}).get("percent", 100)
            hora    = h.get("interval", {}).get("startTime", "")[:16].replace("T", " ")
            if v_vento <= 10 and v_chuva <= 20:
                janelas.append({"hora": hora, "vento": v_vento, "chuva": v_chuva})

        return jsonify({
            "ok": True,
            "atual": {
                "temp":      temp,
                "umidade":   umidade,
                "vento":     vento,
                "condicao":  condicao,
                "graus_dia": calcular_graus_dia(temp, cultura)
            },
            "recomendacoes": {
                "irrigacao":    analisar_para_irrigacao(atual),
                "pulverizacao": analisar_para_pulverizacao(atual),
                "geada":        analisar_geada(previsao_d)
            },
            "janelas_pulverizacao": janelas[:5],
            "previsao_dias": dias
        })

    except Exception as e:
        return jsonify({"ok": False, "erro": str(e)}), 500


@app.route("/api/cache/stats")
def cache_stats():
    return jsonify(cache.stats())


if __name__ == "__main__":
    app.run(debug=True)
