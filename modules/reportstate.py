import os
import io
import json
import time
import requests
import google.auth.crypt
import google.auth.jwt
import modules.config as config

from modules.database import Settings
from modules.helpers import logger

# Google API calls block the request that triggered them; never wait forever
HOMEGRAPH_TIMEOUT = 10


class ReportState:
    """Google Report State implementation."""

    def __init__(self):
        """Log error code."""
        self._access_token = None
        self._access_token_expires = None
        self._retry_after = 0              # no new token request before this time

    @staticmethod
    def report_state_enabled():
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
        # The token expiry is only stored once a token has really been
        # obtained (get_access_token). Storing it here meant that a failed renewal
        # (accounts.google.com timeout) kept the old expired token in use for one
        # more hour: every report state got 401 and Google said "unavailable".

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

        r = requests.post(url, headers=headers, data=data, timeout=HOMEGRAPH_TIMEOUT)

        if r.status_code == requests.codes.ok:
            token_data = json.loads(r.text)
            self._access_token = token_data['access_token']
            # renew one minute early (Google tokens last expires_in seconds, 3599 by default)
            self._access_token_expires = int(time.time()) + int(token_data.get('expires_in', 3600)) - 60
            return token_data['access_token']

        r.raise_for_status()
        return

    @staticmethod
    def call_homegraph_api_key(payload):

        dbsettings = Settings.query.get_or_404(1)

        url = 'https://homegraph.googleapis.com/v1/devices:requestSync?key=' + dbsettings.api_key

        r = requests.post(url, json=payload, timeout=HOMEGRAPH_TIMEOUT)

        if 'error' in r.text:
            logger.error(r.text)

        return r.status_code == requests.codes.ok

    def call_homegraph_api(self, rt, payload):
        """Makes an authorized request to the endpoint"""
        if rt == 'sync':
            url = 'https://homegraph.googleapis.com/v1/devices:requestSync'
            # Without async Google calls our SYNC fulfillment before answering
            payload = {**payload, 'async': True}
        elif rt == 'state':
            url = 'https://homegraph.googleapis.com/v1/devices:reportStateAndNotification'
        now = int(time.time())
        if not self._access_token or now > self._access_token_expires:
            # After a failed renewal, wait 60 s before trying again, so that
            # Google requests are not each held up by a token timeout while the network
            # to Google is down.
            if now < self._retry_after:
                return False
            try:
                self.get_access_token()
            except Exception:
                self._retry_after = now + 60
                raise
        # local copy: another request may reset the token (401) at the same time
        token = self._access_token
        if not token:
            return False

        headers = {
            'X-GFE-SSL': 'yes',
            'Authorization': 'Bearer ' + token
        }

        r = requests.post(url, headers=headers, json=payload, timeout=HOMEGRAPH_TIMEOUT)

        if r.status_code == requests.codes.unauthorized:
            # Token refused, get a new one on the next call
            self._access_token = None
        r.raise_for_status()

        logger.debug("Device state reported %s" % (json.dumps(payload, indent=2, sort_keys=True)))
        return r.status_code == requests.codes.ok
