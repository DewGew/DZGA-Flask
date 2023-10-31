#!/usr/bin/python
# Provides all the API functionality callable through "/api"

from flask import request, flash, redirect, url_for
import flask_login
import json, os, sys
from werkzeug.security import generate_password_hash
from smarthome import report_state
from modules.database import db, User, Settings
from modules.domoticz import getDomoticzDevices, queryDomoticz
from modules.helpers import logger, remove_user, generateToken

def modifyServerSettings(request):

    dbsettings = Settings.query.get_or_404(1)
    
    dbsettings.client_id = request.args.get('aogclient', '')
    dbsettings.client_secret = request.args.get('aogsecret', '')
    dbsettings.api_key = request.args.get('aogapi', '')
    dbsettings.tempunit = request.args.get('tempunit', '')
    dbsettings.language = request.args.get('language', '')
    dbsettings.use_ssl = (request.args.get('ssl', '') == 'true')
    dbsettings.ssl_cert = request.args.get('sslcert', '')
    dbsettings.ssl_key = request.args.get('sslkey', '')
               
    db.session.add(dbsettings)
    db.session.commit()
    
    logger.info("Server settings saved")
    
def modifyUserSettings(username, request):

    dbuser = User.query.filter_by(username=username).first()

    dbuser.domo_url = request.args.get('domourl', '')
    dbuser.domouser = request.args.get('domouser','')
    dbuser.domopass = request.args.get('domopass','')
    dbuser.roomplan = request.args.get('roomplan','')
    dbuser.password = request.args.get('uipassword','')
    dbuser.googleassistant = (request.args.get('googleassistant', '') == 'true')
    #dbuser.authtoken = request.args.get('authtoken','')

    
    db.session.add(dbuser)
    db.session.commit()
    
    logger.info("User settings updated")
    

@flask_login.login_required
def gateway():
    dbsettings = Settings.query.get_or_404(1)
    dbuser = User.query.filter_by(username=flask_login.current_user.username).first()
    requestedUrl = request.url.split("/api")
    custom = request.args.get('custom', '')
    newsettings = {}

    if custom == "sync":
        if dbuser.googleassistant == True:
            if report_state.enable_report_state():
                payload = {"agentUserId": flask_login.current_user.username}
                r = report_state.call_homegraph_api('sync', payload)
                result = '{"title": "RequestedSync", "status": "OK"}'
                flash("Devices synced with domoticz")
            else:
                result = '{"title": "RequestedSync", "status": "ERR"}'
                flash("Error syncing devices with domoticz")
        else:
            getDomoticzDevices(flask_login.current_user.username)
            flash("Devices synced with domoticz")
            return "Devices synced with domoticz", 200
            
    elif custom == "setArmLevel":
        armLevel = request.args.get('armLevel', '')
        seccode = idx = request.args.get('seccode', '')
        result = queryDomoticz(flask_login.current_user.username, '?type=command&param=setsecstatus&secstatus=' + armLevel + '&seccode=' + hashlib.md5(str.encode(seccode)).hexdigest())

    elif custom == "server_settings":

        modifyServerSettings(request)
        
    elif custom == "user_settings":
    
        modifyUserSettings(flask_login.current_user.username, request)
               
    elif custom == "removeuser":
        userToRemove = request.args.get('user','')
        
        removeuser = User.query.filter_by(username=userToRemove).first()
            
        db.session.delete(removeuser)
        db.session.commit()
        remove_user(userToRemove)
        logger.info("User " + userToRemove + " is deleted")

        return "User removed", 200
    else:
        result = queryDomoticz(flask_login.current_user.username, requestedUrl[1])
    try:
        return json.loads(result)
    except:
        return "No results returned", 404