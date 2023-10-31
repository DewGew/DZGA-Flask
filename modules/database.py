from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func, or_
from sqlalchemy_json import mutable_json_type

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "User"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    roomplan = db.Column(db.String(10))
    domo_url = db.Column(db.String(255))
    domouser = db.Column(db.String(100))
    domopass = db.Column(db.String(100))
    admin = db.Column(db.Boolean, default=False, nullable=False)
    googleassistant = db.Column(db.Boolean, default=False, nullable=False)
    authtoken = db.Column(db.String(100))
    
    def __repr__(self):
        return f"<User {self.id}>"
        
class Settings(db.Model):
    __tablename__ = "Settings"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.String(255))
    client_secret = db.Column(db.String(255))
    api_key = db.Column(db.String(255))
    tempunit = db.Column(db.String(255))
    use_ssl = db.Column(db.Boolean, default=False, nullable=False)
    ssl_cert = db.Column(db.String(255))
    ssl_key = db.Column(db.String(255))
    language = db.Column(db.String(255))
    armlevels = db.Column(mutable_json_type(dbtype=db.JSON, nested=True))
    
    def __repr__(self):
        return f"<Settings {self.id}>"