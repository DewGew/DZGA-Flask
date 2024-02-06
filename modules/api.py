#!/usr/bin/python
# Provides all the API functionality callable through "/api"

from flask import request, flash
import flask_login
import json
import os
import sys
import hashlib
from werkzeug.security import generate_password_hash
from smarthome import rs
from modules.database import db, User, Settings
from modules.domoticz import getDomoticzDevices, queryDomoticz
from modules.helpers import logger, remove_user


def modifyServerSettings(request):

    dbsettings = Settings.query.get_or_404(1)

    client_id = request.args.get('aogclient', None)
    if client_id:
        dbsettings.client_id = client_id
    client_secret = request.args.get('aogsecret', None)
    if client_secret:
        dbsettings.client_secret = client_secret
    api_key = request.args.get('aogapi', None)
    if api_key:
        dbsettings.api_key = api_key
    tempunit = request.args.get('tempunit', None)
    if tempunit:
        dbsettings.tempunit = tempunit
    language = request.args.get('language', None)
    if language:
        dbsettings.language = language
    use_ssl = request.args.get('ssl', None)
    if use_ssl:
        dbsettings.use_ssl =(True if use_ssl else False) 
    ssl_cert = request.args.get('sslcert', None)
    if ssl_cert:
        dbsettings.ssl_cert = ssl_cert
    ssl_key = request.args.get('sslkey', None)
    if ssl_key:
        dbsettings.ssl_key = ssl_key

    db.session.add(dbsettings)
    db.session.commit()

    logger.info("Server settings saved")


def modifyUserSettings(username, request):

    dbuser = User.query.filter_by(username=username).first()

    domo_url = request.args.get('domourl', None)
    if domo_url:
        dbuser.domo_url = domo_url
    domouser = request.args.get('domouser', None)
    if domouser:
        dbuser.domouser = domouser
    domopass = request.args.get('domopass', None)
    if domopass:
        dbuser.domopass = domopass
    roomplan = request.args.get('roomplan', None)
    if roomplan:
        dbuser.roomplan = roomplan
    password = request.args.get('uipassword', None)
    if password:
        dbuser.password = password
    googleassistant = request.args.get('googleassistant', None)
    if googleassistant:
        dbuser.googleassistant = (True if googleassistant == 'true' else False)

    db.session.add(dbuser)
    db.session.commit()

    logger.info("User settings updated")

    
def modifyDeviceConfig(username, request):
    
    dbuser = User.query.filter_by(username=username).first()
    deviceconfig = dbuser.device_config
       
    entityId = request.args.get('id', None)
    hide = request.args.get('hide', None)
    checkstate = request.args.get('check_state', None)
    room = request.args.get('room', None)
    ack = request.args.get('ack', None)
    devicetype = request.args.get('devicetype', None)
    nicknames = request.args.get('nicknames', None)

    if entityId:
        if entityId not in deviceconfig.keys():
                deviceconfig[entityId] = {}
        if hide == 'true':
            deviceconfig[entityId].update({'hide': True})
        elif hide is not None and entityId in deviceconfig.keys() and 'hide' in deviceconfig[entityId]:
            deviceconfig[entityId].pop('hide')
            
        if checkstate == 'false':
            deviceconfig[entityId].update({'check_state': False})
        elif checkstate is not None and entityId in deviceconfig.keys() and 'check_state' in deviceconfig[entityId]:
            deviceconfig[entityId].pop('check_state')
            
        if room:
            deviceconfig[entityId].update({'room': room})
            
        if ack == 'true':
            deviceconfig[entityId].update({'ack': True})
        elif ack is not None and entityId in deviceconfig.keys() and 'ack' in deviceconfig[entityId]:
            deviceconfig[entityId].pop('ack')
            
        if devicetype:
            deviceconfig[entityId].update({'devicetype': devicetype})
        
        if nicknames:
            names = nicknames.split(",")
            names = list(filter(None, names))
            deviceconfig[entityId].update({'nicknames': names})
            logger.info(names)

        dbuser.device_config.update(deviceconfig)
        db.session.add(dbuser)
        db.session.commit()
        
        if dbuser.googleassistant is True:
            if rs.report_state_enabled():
                rs.call_homegraph_api('sync', {"agentUserId": username})
        else:
            getDomoticzDevices(username)
                
        logger.info("User settings updated")
        return '{"title": "UserSettingsChanged", "status": "OK"}'
    else:
        return '{"title": "UserSettingsChanged", "status": "ERR"}'

        
    

@flask_login.login_required
def gateway():

    dbuser = User.query.filter_by(username=flask_login.current_user.username).first()
    requestedUrl = request.url.split("/api")
    custom = request.args.get('custom', '')

    if custom == "sync":
        if dbuser.googleassistant is True:
            if rs.report_state_enabled():
                rs.call_homegraph_api('sync', {"agentUserId": flask_login.current_user.username})
                result = '{"title": "RequestedSync", "status": "OK"}'
                flash("Devices synced with domoticz")
            else:
                result = '{"title": "RequestedSync", "status": "ERR"}'
                flash("Error syncing devices with domoticz")
        else:
            getDomoticzDevices(flask_login.current_user.username)
            flash("Devices synced with domoticz")
            result = '{"title": "RequestedSync", "status": "OK"}'

    elif custom == "restart":
        if dbuser.admin:
            logger.info('Restarts smarthome server')
            os.execv(sys.executable, ['python'] + sys.argv)

    elif custom == "setArmLevel":
        armLevel = request.args.get('armLevel', '')
        seccode = request.args.get('seccode', '')
        result = queryDomoticz(flask_login.current_user.username, '?type=command&param=setsecstatus&secstatus=' + armLevel + '&seccode=' + hashlib.md5(str.encode(seccode)).hexdigest())

    elif custom == "server_settings":
        if dbuser.admin:
            modifyServerSettings(request)
            result = '{"title": "ServerSettingsChanged", "status": "OK"}'

    elif custom == "user_settings":

        modifyUserSettings(flask_login.current_user.username, request)
        result = '{"title": "UserSettingsChanged", "status": "OK"}'
        
    elif custom == "device_config":
    
        result = modifyDeviceConfig(flask_login.current_user.username, request)

    elif custom == "removeuser":
        if dbuser.admin:
            userToRemove = request.args.get('user', '')

            removeuser = User.query.filter_by(username=userToRemove).first()

            db.session.delete(removeuser)
            db.session.commit()
            remove_user(userToRemove)
            logger.info("User " + userToRemove + " is deleted")

            result = '{"title": "UserRemoved", "status": "OK"}'
            
    elif '?type' in requestedUrl[1]:

        result = queryDomoticz(flask_login.current_user.username, requestedUrl[1])

    try:
        return json.loads(result), 200
    except Exception:
        return {"title": "No results returned", "status": "ERR"}, 404
