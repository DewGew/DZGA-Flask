import os
import io
import json
import time
import logging
import requests
import google.auth.crypt
import google.auth.jwt
import modules.config as config

from modules.helpers import logger, get_settings

class ReportState:
    """Google Report State implementation."""

    def __init__(self):
        """Log error code."""
        self._access_token = None
        self._access_token_expires = None

    @staticmethod
    def enable_report_state():
        filename = os.path.join(config.KEYFILE_DIRECTORY, "smart-home-key.json")
        if os.path.isfile(filename):
            with open(filename, mode='r') as f:
                f.close()
                return True
        else:
            logger.warning("Service account key is not found. Report state will be unavailable")
            return False

    def generate_jwt(self, keyfile):
        """Generates a signed JSON Web Token using a Google API Service Account."""
        now = int(time.time())
        expires = now + 3600
        self._access_token_expires = expires

        with io.open(keyfile, 'r', encoding='utf-8') as json_file:
            data = json.load(json_file)
            iss = data['client_email']

        # build payload
        payload = {
            'iss': iss,
            'scope': 'https://www.googleapis.com/auth/homegraph',
            'aud': 'https://accounts.google.com/o/oauth2/token',
            'iat': now,
            "exp": expires,
        }

        # sign with keyfile
        signer = google.auth.crypt.RSASigner.from_service_account_file(keyfile)
        jwt = google.auth.jwt.encode(signer, payload)

        return jwt

    def get_access_token(self):
        """Generates a signed JSON Web Token using a Google API Service Account."""
        signed_jwt = self.generate_jwt(os.path.join(config.KEYFILE_DIRECTORY, "smart-home-key.json"))
        if signed_jwt is None:
            return False
        url = 'https://accounts.google.com/o/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = 'grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=' + signed_jwt.decode(
            'utf-8')

        r = requests.post(url, headers=headers, data=data)

        if r.status_code == requests.codes.ok:
            token_data = json.loads(r.text)
            self._access_token = token_data['access_token']
            return token_data['access_token']

        r.raise_for_status()
        return

    @staticmethod
    def call_homegraph_api_key(payload):

        url = 'https://homegraph.googleapis.com/v1/devices:requestSync?key=' + get_settings()['CLIENT_ID']

        r = requests.post(url, json=payload)

        if 'error' in r.text:
            logger.error(r.text)

        return r.status_code == requests.codes.ok

    def call_homegraph_api(self, rt, payload):
        """Makes an authorized request to the endpoint"""
        if rt == 'sync':
            url = 'https://homegraph.googleapis.com/v1/devices:requestSync'
        elif rt == 'state':
            url = 'https://homegraph.googleapis.com/v1/devices:reportStateAndNotification'
        now = int(time.time())
        if not self._access_token or now > self._access_token_expires:
            self.get_access_token()
        elif not self._access_token:
            return

        headers = {
            'X-GFE-SSL': 'yes',
            'Authorization': 'Bearer ' + self._access_token
        }

        r = requests.post(url, headers=headers, json=payload)

        r.raise_for_status()

        logger.debug("Device state reported %s" % (json.dumps(payload, indent=2, sort_keys=True)))
        return r.status_code == requests.codes.ok
