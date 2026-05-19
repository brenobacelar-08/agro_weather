from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from models import db, bcrypt, Usuario, Fazenda
from weather_client import get_condicoes_atuais, get_previsao_diaria, get_previsao_horaria
from agro_analysis import (
    analisar_para_irrigacao,
    analisar_para_pulverizacao,
    analisar_geada,
    calcular_graus_dia
)
import cache
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "climaiagro-secret-2024")
db_url = os.getenv("DATABASE_URL", "sqlite:////tmp/climaiagro.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login_page"

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

with app.app_context():
    db.create_all()


# ─── PÁGINAS ────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/fazendas")
@login_required
def pagina_fazendas():
    fazendas = Fazenda.query.filter_by(usuario_id=current_user.id).all()
    return render_template("fazendas.html",
                           usuario=current_user,
                           fazendas=fazendas)


# ─── AUTH ────────────────────────────────────────────────

@app.route("/auth/cadastro", methods=["POST"])
def cadastro():
    data = request.get_json()
    if Usuario.query.filter_by(email=data["email"]).first():
        return jsonify({"ok": False, "erro": "E-mail já cadastrado."})
    if len(data["senha"]) < 6:
        return jsonify({"ok": False, "erro": "Senha deve ter mínimo 6 caracteres."})

    usuario = Usuario(nome=data["nome"], email=data["email"], plano=data.get("plano", "basico"))
    usuario.set_senha(data["senha"])
    db.session.add(usuario)
    db.session.commit()
    login_user(usuario)
    return jsonify({"ok": True})


@app.route("/auth/login", methods=["POST"])
def fazer_login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(email=data["email"]).first()
    if not usuario or not usuario.check_senha(data["senha"]):
        return jsonify({"ok": False, "erro": "E-mail ou senha incorretos."})
    login_user(usuario)
    return jsonify({"ok": True})


@app.route("/auth/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login_page"))


# ─── API FAZENDAS ─────────────────────────────────────────

@app.route("/api/fazendas", methods=["GET"])
@login_required
def listar_fazendas():
    fazendas = Fazenda.query.filter_by(usuario_id=current_user.id).all()
    return jsonify([f.to_dict() for f in fazendas])


@app.route("/api/fazendas", methods=["POST"])
@login_required
def criar_fazenda():
    count = Fazenda.query.filter_by(usuario_id=current_user.id).count()
    if count >= current_user.limite_fazendas:
        return jsonify({"ok": False, "erro": f"Limite do plano {current_user.plano} atingido."})

    data = request.get_json()
    fazenda = Fazenda(
        nome=data["nome"],
        lat=data["lat"],
        lon=data["lon"],
        cultura=data["cultura"],
        usuario_id=current_user.id
    )
    db.session.add(fazenda)
    db.session.commit()
    return jsonify({"ok": True, "fazenda": fazenda.to_dict()})


@app.route("/api/fazendas/<int:fid>", methods=["DELETE"])
@login_required
def apagar_fazenda(fid):
    fazenda = Fazenda.query.filter_by(id=fid, usuario_id=current_user.id).first()
    if not fazenda:
        return jsonify({"ok": False, "erro": "Fazenda não encontrada."})
    db.session.delete(fazenda)
    db.session.commit()
    return jsonify({"ok": True})


# ─── API CLIMA ────────────────────────────────────────────

@app.route("/api/recomendacao")
@login_required
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
@login_required
def cache_stats():
    return jsonify(cache.stats())


if __name__ == "__main__":
    app.run(debug=True)
