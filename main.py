from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from weather_client import get_condicoes_atuais, get_previsao_diaria
from agro_analysis import (
    analisar_para_irrigacao,
    analisar_para_pulverizacao,
    analisar_geada,
    calcular_graus_dia
)
from config import FAZENDAS

console = Console()


def exibir_fazenda(nome: str, info: dict):
    lat = info["lat"]
    lon = info["lon"]
    cultura = info["cultura"]

    console.print(f"\n[bold green]🌾 {nome}[/bold green]")

    try:
        atual = get_condicoes_atuais(lat, lon)
        temp = atual.get("temperature", {}).get("degrees", "N/A")
        umidade = atual.get("relativeHumidity", "N/A")
        vento = atual.get("wind", {}).get("speed", {}).get("value", "N/A")
        condicao = atual.get("weatherCondition", {}).get("description", {}).get("text", "N/A")

        tabela = Table(title="Condições Atuais", style="cyan")
        tabela.add_column("Parâmetro", style="bold")
        tabela.add_column("Valor")
        tabela.add_row("🌡️  Temperatura", f"{temp}°C")
        tabela.add_row("💧 Umidade", f"{umidade}%")
        tabela.add_row("💨 Vento", f"{vento} km/h")
        tabela.add_row("☁️  Condição", str(condicao))
        tabela.add_row("🌱 Graus-dia", str(calcular_graus_dia(float(temp), cultura)))
        console.print(tabela)

        console.print(Panel(
            f"{analisar_para_irrigacao(atual)}\n{analisar_para_pulverizacao(atual)}",
            title="📋 Recomendações Agronômicas",
            border_style="yellow"
        ))

        previsao = get_previsao_diaria(lat, lon, dias=5)
        console.print("[bold]🌡️  Análise de Geada:[/bold]")
        for alerta in analisar_geada(previsao):
            console.print(f"  {alerta}")

    except Exception as e:
        console.print(f"[red]Erro ao buscar dados: {e}[/red]")


if __name__ == "__main__":
    console.print(Panel(
        "[bold white]🌾 AgroWeather — Sistema de Monitoramento Climático Agrícola[/bold white]",
        style="green"
    ))

    for nome, info in FAZENDAS.items():
        exibir_fazenda(nome, info)

    console.print("\n[dim]Dados fornecidos por Google Weather API[/dim]\n")
