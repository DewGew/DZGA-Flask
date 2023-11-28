import os
import modules.config as config
from time import sleep

from flask_login import login_required, current_user
from flask import (redirect, request, url_for,
                   render_template, session, flash, Response)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from modules.reportstate import ReportState
from modules.database import db, User, Settings
from modules.domoticz import saveJson, getDomoticzDevices
from modules.helpers import logger, get_devices, generateToken, remove_user
from sqlalchemy import or_

report_state = ReportState()


@login_required
def dashboard():

    reportstate = report_state.report_state_enabled()
    devices = get_devices(current_user.username)

    if devices is None:
        getDomoticzDevices(current_user.username)
        devices = get_devices(current_user.username)

    return render_template('dashboard.html',
                           user=User.query.filter_by(username=current_user.username).first(),
                           reportstate=reportstate,
                           devices=devices,
                           _csrf_token=session['_csrf_token']
                           )


@login_required
def devices():

    reportstate = report_state.report_state_enabled()
    dbsettings = Settings.query.get_or_404(1)
    devices = get_devices(current_user.username)
    dbuser = User.query.filter_by(username=current_user.username).first()

    if request.method == "POST":

        deviceconfig = dbuser.device_config

        if request.form['submit'] == 'device_settings':
            idx = request.form.get('device_id')
            hideDevice = request.form.get('hideDevice')
            willReportState = request.form.get('willReportState')
            challenge = request.form.get('2FA')
            # notification = request.form.get('notification')
            room = request.form.get('room')
            nicknames = request.form.get('nicknames')
            devicetype = request.form.get('devicetype')
            minThreehold = request.form.get('minThreehold')
            maxThreehold = request.form.get('maxThreehold')
            camurl = request.form.get('camurl')
            actual_temp_idx = request.form.get('actual_temp_idx')
            selector_modes_idx = request.form.get('selector_modes_idx')

            if idx not in deviceconfig.keys():
                deviceconfig[idx] = {}

            if hideDevice == 'on':
                deviceconfig[idx].update({'hide': True})
            elif idx in deviceconfig.keys() and 'hide' in deviceconfig[idx]:
                deviceconfig[idx].pop('hide')

            if willReportState != 'on':
                deviceconfig[idx].update({'report_state': False})
            elif idx in deviceconfig.keys() and 'report_state' in deviceconfig[idx]:
                deviceconfig[idx].pop('report_state')

            if challenge == 'ackNeeded':
                deviceconfig[idx].update({'ack': True})
            elif idx in deviceconfig.keys() and 'ack' in deviceconfig[idx]:
                deviceconfig[idx].pop('ack')

            # if notification == 'on':
                # deviceconfig[idx].update({'notification': True})
            # elif idx in deviceconfig.keys() and 'notification' in deviceconfig[idx]:
                # deviceconfig[idx].pop('notification')

            if room is not None:
                if room != '':
                    deviceconfig[idx].update({'room': room})
                elif idx in deviceconfig.keys() and 'room' in deviceconfig[idx]:
                    deviceconfig[idx].pop('room')

            if nicknames is not None:
                if nicknames != '':
                    names = nicknames.split(", ")
                    names = list(filter(None, names))
                    deviceconfig[idx].update({'nicknames': names})
                elif idx in deviceconfig.keys() and 'nicknames' in deviceconfig[idx]:
                    deviceconfig[idx].pop('nicknames')

            if devicetype is not None:
                if devicetype != 'default':
                    deviceconfig[idx].update({'devicetype': devicetype})
                elif idx in deviceconfig.keys() and 'devicetype' in deviceconfig[idx]:
                    deviceconfig[idx].pop('devicetype')

            if minThreehold is not None:
                if minThreehold != '':
                    deviceconfig[idx].update({'minThreehold': int(minThreehold)})
                elif idx in deviceconfig.keys() and 'minThreehold' in deviceconfig[idx]:
                    deviceconfig[idx].pop('minThreehold')

            if maxThreehold is not None:
                if maxThreehold != '':
                    deviceconfig[idx].update({'maxThreehold': int(maxThreehold)})
                elif idx in deviceconfig.keys() and 'maxThreehold' in deviceconfig[idx]:
                    deviceconfig[idx].pop('maxThreehold')

            if actual_temp_idx is not None:
                if actual_temp_idx != '':
                    deviceconfig[idx].update({'actual_temp_idx': actual_temp_idx})
                elif idx in deviceconfig.keys() and 'actual_temp_idx' in deviceconfig[idx]:
                    deviceconfig[idx].pop('actual_temp_idx')

            if selector_modes_idx is not None:
                if selector_modes_idx != '':
                    deviceconfig[idx].update({'selector_modes_idx': selector_modes_idx})
                elif idx in deviceconfig.keys() and 'selector_modes_idx' in deviceconfig[idx]:
                    deviceconfig[idx].pop('selector_modes_idx')

            if camurl is not None:
                if camurl != '':
                    deviceconfig[idx].update({'camurl': camurl})
                elif idx in deviceconfig.keys() and 'camurl' in deviceconfig[idx]:
                    deviceconfig[idx].pop('camurl')

            if deviceconfig[idx] == {}:
                deviceconfig.pop(idx)

            dbuser.device_config.update(deviceconfig)
            db.session.add(dbuser)
            db.session.commit()

            armedhome = request.form.get('armedhome')
            armedaway = request.form.get('armedaway')
            if (armedhome is not None) or (armedaway is not None):
                armedhome = armedhome.split(", ")
                armedaway = armedaway.split(", ")
                armhome = list(filter(None, armedhome))
                armaway = list(filter(None, armedaway))
                dbsettings.armlevels.update({'armhome': armhome, 'armaway': armaway})

                db.session.add(dbsettings)
                db.session.commit()

        logger.info("Device settings saved")

        return redirect(url_for('devices'))

    if request.method == "GET":

        return render_template('devices.html',
                               user=dbuser,
                               dbsettings=dbsettings,
                               reportstate=reportstate,
                               devices=devices,
                               _csrf_token=session['_csrf_token']
                               )


@login_required
def logging():
    dbsettings = Settings.query.get_or_404(1)

    return render_template('logging.html',
                           user=User.query.filter_by(username=current_user.username).first(),
                           dbsettings=dbsettings)


@login_required
def stream():
    """returns logging information"""
    def generate():
        filename = os.path.join(config.CONFIG_DIRECTORY, "smarthome.log")
        with open(filename) as f:
            while True:
                yield f.read()
                sleep(0.5)

    return Response(generate(), mimetype='text/plain')


@login_required
def settings():

    if request.method == "POST":

        dbuser = User.query.filter_by(username=current_user.username).first()
        dbsettings = Settings.query.get_or_404(1)

        if request.form['submit'] == 'save_user_settings':
            dbuser.domo_url = request.form.get('domourl')
            dbuser.domouser = request.form.get('domouser')
            dbuser.domopass = request.form.get('domopass')
            dbuser.roomplan = request.form.get('roomplan')
            dbuser.password = request.form.get('uipassword')  # Remove ?
            dbuser.googleassistant = (request.form.get('googleassist') == 'true')  # Remove ?

            db.session.add(dbuser)
            db.session.commit()

        if request.form['submit'] == 'save_server_settings':

            dbsettings.client_id = request.form.get('aogclient')
            dbsettings.client_secret = request.form.get('aogsecret')
            api_key = request.form.get('aogapi')
            if api_key is not None:
                dbsettings.api_key = api_key
            dbsettings.tempunit = request.form.get('tempunit')
            dbsettings.language = request.form.get('language')
            dbsettings.use_ssl = (request.form.get('ssl') == 'true')
            dbsettings.ssl_cert = request.form.get('sslcert')
            dbsettings.ssl_key = request.form.get('sslkey')

            db.session.add(dbsettings)
            db.session.commit()

        if request.form['submit'] == 'new_user':

            newuser = request.form.get('user')
            newpass = request.form.get('userpassword')
            newemail = request.form.get('email')
            newadmin = (request.form.get('admin') == 'true')
            newgoogleassistant = (request.form.get('googleassistant') == 'true')

            userExist = db.session.query(User).filter(or_(User.email == newemail, User.username == newuser)).first()
            if userExist:
                flash('Email address or username already exists!')
                return redirect(url_for('settings'))

            add_new_user = User(email=newemail, username=newuser, password=newpass,
                                roomplan='0', domo_url='http://192.168.1.99:8080', domouser='domoticz', domopass='password',
                                admin=newadmin, googleassistant=newgoogleassistant, authtoken=generateToken(newuser), device_config={})

            db.session.add(add_new_user)
            db.session.commit()

            data = {}
            saveJson(newuser, data)

        if 'modify_user_' in request.form['submit']:

            usertomodify = request.form['submit']
            usertomodify = usertomodify.replace('modify_user_', '')

            moduser = User.query.filter_by(username=usertomodify).first()
            moduser.email = request.form.get('email_' + usertomodify)
            moduser.password = request.form.get('userpassword_' + usertomodify)
            moduser.admin = (request.form.get('admin_' + usertomodify) == 'true')
            moduser.googleassistant = (request.form.get('googleassist_' + usertomodify) == 'true')

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
        reportstate = report_state.report_state_enabled()
        devices = get_devices(current_user.username)

        return render_template('settings.html',
                               user=User.query.filter_by(username=current_user.username).first(),
                               dbsettings=dbsettings,
                               dbusers=dbusers,
                               reportstate=reportstate,
                               devices=devices,
                               _csrf_token=session['_csrf_token']
                               )


@login_required
def uploader():

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
