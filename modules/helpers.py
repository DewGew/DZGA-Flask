# -*- coding: utf-8 -*-

import os
import json
import logging
from flask import request, session, abort

import random
import string
import modules.config as config

# Logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(asctime)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    filename=os.path.join(config.CONFIG_DIRECTORY, "smarthome.log"),
                    filemode='w')
logging.getLogger().addHandler(logging.StreamHandler())
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logger = logging.getLogger()


def remove_user(user):
    devicesfile = os.path.join(config.DEVICES_DIRECTORY, user + "_devices.json")
    os.remove(devicesfile)


# Function to retrieve token from header #
def get_token():
    auth = request.headers.get('Authorization')
    parts = auth.split(' ', 2)
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        return parts[1]
    else:
        logger.warning("invalid token: %s", auth)
        return None


# Function to load device info
def getVersion():
    filename = os.path.join("VERSION.md")
    if os.path.isfile(filename) and os.access(filename, os.R_OK):
        with open(filename, mode='r') as f:
            text = f.read()
            text = text.split()

            return text[0]
    else:
        return None
        

# Function to check current token, returns username #
def check_token():
    access_token = get_token()
    access_token_file = os.path.join(config.TOKENS_DIRECTORY, access_token)
    if os.path.isfile(access_token_file) and os.access(access_token_file, os.R_OK):
        with open(access_token_file, mode='r') as f:
            return f.read()
    else:
        return None


# Function to load device info
def get_device(user_id, device_id):
    filename = os.path.join(config.DEVICES_DIRECTORY, user_id + "_devices.json")
    if os.path.isfile(filename) and os.access(filename, os.R_OK):
        with open(filename, mode='r') as f:
            text = f.read()
            jdata = json.loads(text)
            data = jdata[device_id]
            data['id'] = device_id
            return data
    else:
        return None


# Function to load devices info
def get_devices(user_id):
    filename = os.path.join(config.DEVICES_DIRECTORY, user_id + "_devices.json")
    if os.path.isfile(filename) and os.access(filename, os.R_OK):
        with open(filename, mode='r') as f:
            text = f.read()
            data = json.loads(text)
            return data
    else:
        return None


# Random string generator
def random_string(stringLength=8):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for i in range(stringLength))


def _tempConvert(temp, unit):
    """ Convert Fahrenheit to Celsius """
    if unit == 'F':
        celsius = (temp - 32) * 5 / 9
        return celsius
    else:
        return temp

  
def generateToken(last_code_user):
    access_token = random_string(32)
    logger.info("Access granted for " + last_code_user)

    return access_token


def csrfProtect():
    if request.method == "POST":
        token = session.get('_csrf_token')
        if not token or token != request.form['_csrf_token']:
            abort(403)


def generateCsrfToken():
    if '_csrf_token' not in session:
        session['_csrf_token'] = generate_API_key()
    return session['_csrf_token']


def generate_API_key():
    return random_string(16)

class SmartHomeError(Exception):
    def __init__(self, code, msg):
        """Log error code."""
        super().__init__(msg)
        self.code = code
        
class SmartHomeErrorNoChallenge(Exception):
    def __init__(self, code, desc, msg):
        """Log error code."""
        super().__init__(msg)
        self.code = code
        self.desc = desc
