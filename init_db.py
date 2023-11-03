from flask import Flask
from werkzeug.security import generate_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_json import mutable_json_type
from modules.helpers import logger, generateToken

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
db = SQLAlchemy(app)


class User(db.Model):
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


with app.app_context():
    db.create_all()
    email = 'admin@example.com'
    username = 'admin'
    new_user = User(email=email,
                    username=username,
                    # password=generate_password_hash('smarthome'),
                    password='smarthome',
                    roomplan='0',
                    domo_url='http://192.168.1.99:8080',
                    domouser='domoticz',
                    domopass='password',
                    admin=True,
                    googleassistant=True,
                    authtoken=generateToken(username),
                    )
    db.session.add(new_user)

    settings = Settings(client_id='sampleClientId',
                        client_secret='sampleClientSecret',
                        api_key='<aog_api_key>',
                        tempunit='C',
                        use_ssl=False,
                        ssl_cert='/home/cert/local.crt',
                        ssl_key='/home/cert/local.key',
                        language='en',
                        armlevels={'armhome': [
                                        "armed home",
                                        "low security",
                                        "home and guarding",
                                        "level 1",
                                        "home",
                                        "SL1"],
                                   'armaway': [
                                        "armed away",
                                        "high security",
                                        "away and guarding",
                                        "level 2",
                                        "away",
                                        "SL2"]
                                   }
                        )
    db.session.add(settings)
    try:
        db.session.commit()
        logger.info("Database is created...")
    except Exception:
        logger.info('Database already created')
