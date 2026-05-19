from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)
    plano = db.Column(db.String(20), default="basico")
    criado_em = db.Column(db.DateTime, server_default=db.func.now())

    fazendas = db.relationship("Fazenda", backref="usuario", lazy=True, cascade="all, delete")

    def set_senha(self, senha):
        self.senha_hash = bcrypt.generate_password_hash(senha).decode("utf-8")

    def check_senha(self, senha):
        return bcrypt.check_password_hash(self.senha_hash, senha)

    @property
    def limite_fazendas(self):
        return {"basico": 3, "pro": 10, "enterprise": 999}.get(self.plano, 3)


class Fazenda(db.Model):
    __tablename__ = "fazendas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lon = db.Column(db.Float, nullable=False)
    cultura = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "lat": self.lat,
            "lon": self.lon,
            "cultura": self.cultura
        }
