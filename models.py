from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Profile(db.Model, UserMixin):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    bairro = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    
    __mapper_args__ = {
        'polymorphic_identity': 'profile',
        'polymorphic_on': tipo
    }

    # Implementing UserMixin methods
    def is_active(self):
        return True

    def is_authenticated(self):
        return True

    def is_anonymous(self):
        return False

class User(Profile):
    __tablename__ = 'users'
    id = db.Column(db.Integer, db.ForeignKey('profiles.id'), primary_key=True)
    shop_name = None
    atuacao = None
    __mapper_args__ = {
        'polymorphic_identity': 'user',
    }

class Merchant(Profile):
    __tablename__ = 'merchants'
    id = db.Column(db.Integer, db.ForeignKey('profiles.id'), primary_key=True)
    shop_name = db.Column(db.String, nullable=False)
    atuacao = db.Column(db.String, nullable=False)
    
    products = db.relationship('Product', backref='merchant', lazy=True)

    __mapper_args__ = {
        'polymorphic_identity': 'merchant',
    }

class Charity(Profile):
    __tablename__ = 'charities'
    id = db.Column(db.Integer, db.ForeignKey('profiles.id'), primary_key=True)
    shop_name = db.Column(db.String, nullable=False)
    atuacao = db.Column(db.String, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'charity',
    }

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=True)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, nullable=True)
    qr_code = db.Column(db.String, nullable=True)  # Store the QR code as a string (URL or base64)
    visible = db.Column(db.Boolean, default=False, nullable=False)
    path = db.Column(db.String,nullable=False)
    merchant_id = db.Column(db.Integer, db.ForeignKey('merchants.id'), nullable=False)
