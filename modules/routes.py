import flask_login
import modules.api as api

from flask import Flask, redirect, request, url_for, render_template, send_from_directory, jsonify, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from modules.reportstate import ReportState
from modules.database import db, User, Settings
from modules.domoticz import saveJson, getDomoticzDevices
from modules.helpers import logger, get_device, get_devices, generateToken, remove_user
from sqlalchemy import or_

report_state = ReportState()

@flask_login.login_required
def dashboard():

    reportstate = report_state.enable_report_state() 
    devices = get_devices(flask_login.current_user.username)
    
    if devices == None:
        getDomoticzDevices(flask_login.current_user.username)
        devices = get_devices(flask_login.current_user.username)

    return render_template('dashboard.html',
        user = User.query.filter_by(username=flask_login.current_user.username).first(),
        reportstate = reportstate,
        devices = devices,
        _csrf_token=session['_csrf_token']        
        )
        
@flask_login.login_required
def devices():
    reportstate = report_state.enable_report_state()
    dbsettings = Settings.query.get_or_404(1)
    devices = get_devices(flask_login.current_user.username)

    return render_template('devices.html',
        user = User.query.filter_by(username=flask_login.current_user.username).first(),
        dbsettings = dbsettings,
        reportstate = reportstate,
        devices = devices,
        _csrf_token=session['_csrf_token']        
        )
        
@flask_login.login_required
def logging():
    dbsettings = Settings.query.get_or_404(1)

    return render_template('logging.html',
        user = User.query.filter_by(username=flask_login.current_user.username).first(),
        dbsettings = dbsettings)

@flask_login.login_required
def settings():

    if request.method == "POST":
    
        dbuser = User.query.filter_by(username=flask_login.current_user.username).first()
        dbsettings = Settings.query.get_or_404(1)
    
        if request.form['submit'] == 'save_user_settings':
        
            dbuser.domo_url = request.form.get('domourl')
            dbuser.domouser = request.form.get('domouser')
            dbuser.domopass = request.form.get('domopass')
            dbuser.roomplan = request.form.get('roomplan')
            dbuser.password = request.form.get('uipassword') # Remove ?
            dbuser.googleassistant = (request.form.get('googleassistant') == 'true') # Remove ?
            
            db.session.add(dbuser)
            db.session.commit()
            
        if request.form['submit'] == 'save_server_settings':
           
            dbsettings.client_id = request.form.get('aogclient')
            dbsettings.client_secret = request.form.get('aogsecret')
            dbsettings.api_key = request.form.get('aogapi')
            dbsettings.tempunit = request.form.get('tempunit')
            dbsettings.language = request.form.get('language')
            dbsettings.use_ssl = (request.form.get('ssl') == 'true')
            dbsettings.ssl_cert = request.form.get('sslcert')
            dbsettings.ssl_key = request.form.get('sslkey')
            #dbsettings.armhome = request.form.get('armhome')
            #dbsettings.armaway = request.form.get('armaway')
                       
            db.session.add(dbsettings)
            db.session.commit()
            
        if request.form['submit'] == 'new_user':
            
            newuser = request.form.get('user')
            newpass = request.form.get('userpassword')
            newemail = request.form.get('email')
            newadmin = (request.form.get('admin') == 'true')
            newgoogleassistant = (request.form.get('googleassistant') == 'true')
            
            userExist = db.session.query(User).filter(or_(User.email==newemail, User.username==newuser)).first()
            if userExist:
                flash('Email address or username already exists!')
                return redirect(url_for('settings'))
                
            add_new_user = User(email=newemail, username=newuser, password=newpass,
                            roomplan='0', domo_url='http://192.168.1.13:8080', domouser='domoticz', domopass='password',
                            admin=newadmin, googleassistant=newgoogleassistant, authtoken=generateToken(newuser))
                            
            db.session.add(add_new_user)
            db.session.commit()
            
            data = {}
            saveJson(newuser, data)

        if 'modify_user_' in request.form['submit']:
        
            usertomodify = request.form['submit']
            usertomodify = usertomodify.replace('modify_user_', '')
 
            moduser = User.query.filter_by(username=usertomodify).first()
            moduser.email = request.form.get('email_'+ usertomodify)
            moduser.password = request.form.get('userpassword_'+ usertomodify)
            moduser.admin = (request.form.get('admin_'+ usertomodify) == 'true')
            moduser.googleassistant = (request.form.get('googleassist_'+ usertomodify) == 'true')
            
            db.session.add(moduser)
            db.session.commit()
            
        if 'remove_user_' in request.form['submit']:
            usertoremove = request.form['submit']
            usertoremove = usertoremove.replace('remove_user_', '')
            removeuser = User.query.filter_by(username=usertoremove).first()
            
            db.session.delete(removeuser)
            db.session.commit()
            remove_user(usertoremove)
            
            logger.info("User " + usertoremove + " removed!")
            
        flash('Settings saved')  
        logger.info('Settings Saved!')    
            
        return redirect(url_for('settings'))

    if request.method == "GET":
        dbsettings = Settings.query.get_or_404(1)
        dbusers = User.query.all()
        
        reportstate = report_state.enable_report_state()
        devices = get_devices(flask_login.current_user.username)

        return render_template('settings.html',
            user = User.query.filter_by(username=flask_login.current_user.username).first(),
            dbsettings = dbsettings,
            dbusers = dbusers,
            reportstate = reportstate,
            devices = devices,
            _csrf_token=session['_csrf_token']        
            )
        