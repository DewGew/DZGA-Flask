# -*- coding: utf-8 -*-

import flask_login
import importlib
import urllib
import os, sys, json
import hashlib
import modules.config as config
import modules.api as api
import modules.routes as routes

from time import time, sleep
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from modules.database import db, User, Settings
from modules.domoticz import getDomoticzDevices
from modules.helpers import logger, get_token, random_string, get_device, get_devices,
                            generateToken, generateCsrfToken, csrfProtect
from modules.reportstate import ReportState
from flask import Flask, redirect, request, url_for, render_template,
                  send_from_directory, jsonify, session, flash, Response
from sqlalchemy import or_

# Path to traits
sys.path.insert(0, 'modules')

app = Flask(__name__)
# Create an actual secret key for production
app.secret_key = 'secret'
# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Needed for use with reverse proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
# Init database
db.init_app(app)
app.json.sort_keys = False
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
report_state = ReportState()


last_code = None
last_code_user = None
last_code_time = None

logger.info("Smarthome has started.")

if report_state.enable_report_state():
    logger.info('Smart-home-key.json found')
else:
    logger.info('Save the smart-home-key.json in %s folder', config.KEYFILE_DIRECTORY)
        
@login_manager.user_loader
def user_loader(username):
    return db.session.get(User,int(username))

@login_manager.request_loader
def request_loader(request):
    if session:
        csrfProtect()

    authtoken = request.headers.get('Authorization')
    if authtoken:
        token = get_token()
        user = User.query.filter_by(authtoken=token).first()
        if user.username:
            return user
    
    return None    
    
@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('login'))
    
def statereport(requestId, userID, states):
    """Send a state report to Google."""

    data = {}
    data['requestId'] = requestId
    data['agentUserId'] = userID
    data['payload'] = {}
    data['payload']['devices'] = {}
    data['payload']['devices']['states'] = states 
    
    report_state.call_homegraph_api('state', data) 

@app.context_processor
def handle_context():
    """Inject object into jinja2 templates."""
    return dict(os=os)
    
## Routes
@app.route('/static/css/<path:path>')
def send_css(path):
    return  send_from_directory('static/css', path)
    
@app.route('/static/js/<path:path>')
def send_js(path):
    return  send_from_directory('static/js', path)
    
@app.route('/uploads/<path:path>')
def send_uploads(path):
    return  send_from_directory('uploads', path)
       
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return  render_template('login.html')

    username = request.form['username']
    password = request.form['password']

    user = db.session.query(User).filter(or_(User.email==username, User.username==username)).first()

    #if not user or not check_password_hash(user.password, password):
    if not user or (user.password != password):
        if "X-Real-Ip" in request.headers:
            logger.warning("Login failed from %s", request.headers["X-Real-Ip"])
        return render_template('login.html', login_failed=True)

    #elif user and check_password_hash(user.password, password):
    elif user and (user.password == password):
        flask_login.login_user(user)
    
    generateCsrfToken()
    return redirect(url_for('dashboard'))
    
# OAuth entry point
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    global last_code, last_code_user, last_code_time
    dbsettings = Settings.query.get_or_404(1)
   
    if request.method == 'GET':    
        return  render_template('login.html')
    if request.method == 'POST':
        if ("username" not in  request.form
                or "password" not in  request.form
                or "state" not in request.args
                or "response_type" not in request.args
                or request.args["response_type"] != "code"
                or "client_id" not in request.args
                or request.args["client_id"] != dbsettings.client_id):
                    logger.warning("invalid auth request")
                    return "Invalid request", 400
    # Check login and password
    username = request.form['username']
    password = request.form['password']
    
    user = db.session.query(User).filter(or_(User.email==username, User.username==username)).first()
    
    #if user and check_password_hash(user.password, password):
    if user and (user.password == password):
        flask_login.login_user(user)
        
        # Generate random code and remember this user and time
        last_code = random_string(8)
        last_code_user = (request.form)["username"]
        last_code_time = time()

        params = {'state': request.args['state'], 
                  'code': last_code,
                  'client_id': dbsettings.client_id}
        logger.info("generated code")
        return redirect(request.args["redirect_uri"] + '?' + urllib.parse.urlencode(params))
        
    if "X-Real-Ip" in request.headers:
        logger.warning("Login failed from %s", request.headers["X-Real-Ip"])
    return  render_template('login.html', login_failed=True)

# OAuth, token request
@app.route('/token', methods=['POST'])
def token():
    global last_code, last_code_user, last_code_time
    dbsettings = Settings.query.get_or_404(1)
    
    if ("client_secret" not in  request.form
        or request.form["client_secret"] != dbsettings.client_secret
        or "client_id" not in  request.form
        or request.form["client_id"] != dbsettings.client_id
        or "code" not in  request.form):
            logger.warning("invalid token request")
            return "Invalid request", 400
    # Check code
    if ( request.form)["code"] != last_code:
        logger.warning("invalid code")
        return "Invalid code", 403
    # Check time
    if  time() - last_code_time > 10:
        logger.warning("code is too old")
        return "Code is too old", 403
    # Get token with username
    dbuser = User.query.filter_by(username=last_code_user).first()
    access_token = dbuser.authtoken
    # Return token without any expiration time
    return jsonify({'access_token': access_token})
    
# Notification request
@flask_login.login_required
@app.route('/notification', methods=['POST'])
def notification():  
    user_id = flask_login.current_user.username
    user = User.query.filter_by(username=user_id).first()
    
    if user.googleassistant == False:
        return "Not found", 404
    
    # Reportstate must be enabled to use notification 
    if report_state.enable_report_state():
        event_id = random_string(10)
        request_id = random_string(20)
        data = {'requestId': str(request_id),
            'agentUserId': user_id,
            'eventId': str(event_id),
            'payload': {}}      
        try:
            message = request.get_json()
            device =  get_device(user_id, message["id"])
            domain = device['customData']['domain']
        except:
            return '{"title": "SendNotification", "status": "ERR"}'
        # Send smokedetektor notification 
        if domain == 'SmokeDetector':
            data['payload'] = {'devices': {'states': {message["id"]: {'on': (True if message["state"].lower() in ['on', 'alarm/fire !'] else False)}},
                                           'notifications': {message["id"]: {'SensorState': {'priority': 0,'name': 'SmokeLevel','currentSensorState': 'smoke detected'}}}
                        }
                    }
        
        # Send smokedetektor notification 
        elif domain == 'Doorbell':
            data['payload'] = {'devices': {'states': {message["id"]: {'on': (True if message["state"].lower() in ['on', 'pressed'] else False)}},
                                           'notifications': {message["id"]: {"ObjectDetection": {"objects": {"unfamiliar": 1}, 'priority': 0, 'detectionTimestamp': time()}}}                           
                        }
                    }
        else:
            return '{"title": "SendNotification", "status": "ERR"}'
            
        report_state.call_homegraph_api('state', data)
        return '{"title": "SendNotification", "status": "OK"}'
        
    return "Not found", 404
    
# Main URL to interact with Google requests
@flask_login.login_required
@app.route('/smarthome', methods=['POST'])
def fulfillment():
    user_id = flask_login.current_user.username
    user = User.query.filter_by(username=user_id).first()
    
    if user.googleassistant == False:
        return "Not found", 404

    r = request.get_json()

    logger.debug("request: \r\n%s", json.dumps(r, indent=4))
    
    result = {}
    result['requestId'] = r['requestId']
          
    inputs = r['inputs']
    for i in inputs:
        intent = i['intent']
        """ Sync intent, need to response with devices list """
        if intent == "action.devices.SYNC":
            getDomoticzDevices(user_id)
            result['payload'] = {"agentUserId": user_id, "devices": []}
            devs = get_devices(user_id)
            for device_id in devs.keys():
                # Loading device info
                device =  get_device(user_id, device_id)
                if 'Hidden' not in device['customData']['domain']:
                    device['deviceInfo'] = {
                                "manufacturer": "Domoticz",
                                "model": "1",
                                "hwVersion": "1",
                                "swVersion": "1"
                            }
                    result['payload']['devices'].append(device)

        """ Query intent, need to response with current device status """
        if intent == "action.devices.QUERY":
            devs = get_devices(user_id)
            result['payload'] = {}
            result['payload']['devices'] = {}
            for device in i['payload']['devices']:
                device_id = device['id']
                x = devs.get(device_id)
                custom_data = device.get("customData", None)
                device_module = importlib.import_module('trait')
                # Call query method for this device
                query_method = getattr(device_module, "query")
                result['payload']['devices'][device_id] = query_method(custom_data, x, user_id)
            # ReportState    
            if report_state.enable_report_state():
                statereport(result['requestId'],user_id, result['payload']['devices'])
                
        """ Execute intent, need to execute some action """
        if intent == "action.devices.EXECUTE":
            result['payload'] = {}
            result['payload']['commands'] = []
            for command in i['payload']['commands']:
                for device in command['devices']:
                    device_id = device['id']
                    custom_data = device.get("customData", None)
                    device_module = importlib.import_module('trait')
                    # Call execute method for this device for every execute command
                    action_method = getattr(device_module, "execute")
                    for e in command['execution']:
                        command = e['command']
                        params = e.get("params", None)
                        challenge = e.get("challenge", None)
                        acknowledge = custom_data.get('acknowledge', None)
                        protected = custom_data.get('protected', None)
                        if protected:
                            acknowledge = False
                            if challenge is None:
                                action_result = {"status": "ERROR", "errorCode": "challengeNeeded", "challengeNeeded": { "type": "pinNeeded"}, "ids": [device_id]}
                                result['payload']['commands'].append(action_result)
                                logger.debug("response: \r\n%s", json.dumps(result, indent=4))
                                return jsonify(result)
                            elif not challenge.get('pin', False):
                                action_result = {"status": "ERROR", "errorCode": "challengeNeeded", "challengeNeeded": { "type": "userCancelled"}, "ids": [device_id]}
                                result['payload']['commands'].append(action_result)
                                logger.debug("response: \r\n%s", json.dumps(result, indent=4))
                                return jsonify(result)
                        if acknowledge:
                            if challenge is None:                            
                                action_result = {"status": "ERROR", "errorCode": "challengeNeeded", "challengeNeeded": { "type": "ackNeeded"}, "ids": [device_id]}
                                result['payload']['commands'].append(action_result)
                                logger.debug("response: \r\n%s", json.dumps(result, indent=4))
                                return jsonify(result)                               
                        action_result = action_method(custom_data, command, params, user_id, challenge)
                        result['payload']['commands'].append(action_result)
                        action_result['ids'] = [device_id]
            # ReportState           
            if report_state.enable_report_state() and action_result['status'] == 'SUCCESS':
                data = {}
                data[device_id] = action_result['states']
                statereport(result['requestId'], user_id, data)
        
        """ Disconnect intent, need to revoke token """
        if intent == "action.devices.DISCONNECT":
            access_token = get_token()
            user.authtoken = generateToken(user)
            db.session.add(user)
            db.session.commit()
                
            return {}
    
    logger.debug("response: \r\n%s", json.dumps(result, indent=4))
            
    return jsonify(result)

@app.route('/')
def index():

    return redirect(url_for('login'))
        
@app.route("/log_stream", methods=["GET"])
@flask_login.login_required
def stream():
    """returns logging information"""
    def generate():
        filename = os.path.join(config.CONFIG_DIRECTORY, "smarthome.log")
        with open(filename) as f:
            while True:
                yield f.read()
                sleep(0.5)
    return Response(generate(), mimetype='text/plain')
   
        
@app.route('/uploader', methods = ['POST'])
@flask_login.login_required
def upload_file():
   if request.method == 'POST':
        f = request.files['file']
        if f.filename != '':
            file_ext = os.path.splitext(f.filename)[1]
            if file_ext not in ['.jpg', '.png', '.json']:
                logger.warning("Uploadfile is not allowed")
                flash("Uploadfile is not allowed, '.jpg','.png' files or 'smart-home-key.json' is allowed!")
            else:
                f.save(os.path.join(config.UPLOAD_DIRECTORY, secure_filename(f.filename)))
                logger.info("Upload success")
        return redirect(url_for('settings'))
      
@app.route('/logout')
def logout():
    flask_login.logout_user()
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.add_url_rule('/dashboard' , 'dashboard', routes.dashboard, methods=['GET', 'POST'])
    app.add_url_rule('/devices' , 'devices', routes.devices, methods=['GET', 'POST'])
    app.add_url_rule('/logging' , 'logging', routes.logging, methods=['GET', 'POST'])
    app.add_url_rule('/settings' , 'settings', routes.settings, methods=['GET', 'POST'])
    app.add_url_rule('/api', 'api', api.gateway, methods=['POST'])
    app.run('0.0.0.0', port=8181, debug=True) # Need to fix this!!  
    # if dbs.use_ssl:
        # context = (dbs.ssl_cert, dbs.ssl_key)
        # app.run('0.0.0.0', port=8181, debug=True, ssl_context=context)
    # else:
        # app.run('0.0.0.0', port=8181, debug=True)
