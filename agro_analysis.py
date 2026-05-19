def analisar_para_irrigacao(dados_atuais: dict) -> str:
    umidade = dados_atuais.get("relativeHumidity", 0)
    chuva = dados_atuais.get("precipitation", {}).get("probability", {}).get("percent", 0)

    if chuva > 70:
        return "🌧️  SUSPENDER irrigação — chuva prevista (>70%)"
    elif umidade < 40:
        return "💧 URGENTE: Iniciar irrigação — umidade crítica (<40%)"
    elif umidade < 60:
        return "💧 Recomendado irrigar — umidade baixa"
    else:
        return "✅ Irrigação não necessária no momento"


def analisar_para_pulverizacao(dados_atuais: dict) -> str:
    vento = dados_atuais.get("wind", {}).get("speed", {}).get("value", 0)
    chuva = dados_atuais.get("precipitation", {}).get("probability", {}).get("percent", 0)
    umidade = dados_atuais.get("relativeHumidity", 0)

    if chuva > 50:
        return "❌ NÃO pulverizar — risco de chuva"
    elif vento > 15:
        return "❌ NÃO pulverizar — vento acima de 15 km/h"
    elif umidade > 85:
        return "⚠️  Atenção: umidade alta pode reduzir eficácia"
    else:
        return "✅ Condições adequadas para pulverização"


def analisar_geada(previsao_diaria: dict) -> list:
    alertas = []
    dias = previsao_diaria.get("forecastDays", [])
    for i, dia in enumerate(dias):
        temp_min = dia.get("minTemperature", {}).get("degrees", 99)
        if temp_min <= 2:
            alertas.append(f"🥶 ALERTA GEADA — Dia +{i+1}: mínima de {temp_min:.1f}°C")
    return alertas if alertas else ["✅ Sem risco de geada nos próximos dias"]


def calcular_graus_dia(temp_media: float, cultura: str) -> float:
    """
    Graus-dia acumulados no dia para desenvolvimento da cultura.
    Temperaturas base: Soja=10°C | Milho=10°C | Café=13°C
    """
    base = {"soja": 10, "milho": 10, "cafe": 13}.get(cultura, 10)
    return round(max(0, temp_media - base), 2)
