import modules.trait as trait

from itertools import product
from modules.reportstate import ReportState
from modules.helpers import (
        logger,
        get_device,
        get_devices,
        random_string,
        SmartHomeError,
        SmartHomeErrorNoChallenge
        )

repstate = ReportState()


class SmartHomeHandler:

    def statereport(self, requestId, userID, states):
        """Send a state report to Google."""

        data = {'requestId': requestId,
                'agentUserId': userID,
                'payload': {
                    'devices': states
                    }
                }
        if 'notifications' in states:
            data['eventId'] = random_string(10)

        repstate.call_homegraph_api('state', data)

    def sync(self, user_id):

        devices = []
        devs = get_devices(user_id)

        for device_id in devs.keys():
            device = get_device(user_id, device_id)
            if 'Hidden' not in device['customData']['domain']:
                device['deviceInfo'] = {
                            'manufacturer': "Domoticz",
                            'model': '2023.2',
                            'hwVersion': '1.0',
                            'swVersion': '1.0'
                        }
                devices.append(device)

        return {"agentUserId": user_id, "devices": devices}

    def query(self, user_id, payload, requestId):

        devices = {}
        devs = get_devices(user_id)

        for device in payload['devices']:
            attr = devs.get(device['id'])
            custom_data = device.get("customData", None)
            devices[device['id']] = trait.query(custom_data, attr, user_id)

        if repstate.report_state_enabled():
            data = {'states': devices}
            self.statereport(requestId, user_id, data)

        return {'devices': devices}

    def execute(self, user_id, commands, requestId):

        response = {'commands': []}

        for command in commands:
            for device, execution in product(command['devices'], command['execution']):

                custom_data = device['customData']
                params = execution.get('params', None)
                challenge = execution.get('challenge', None)
                command = execution.get('command', None)
                acknowledge = custom_data.get('acknowledge', None)
                protected = custom_data.get('protected', None)
                if protected:
                    acknowledge = False
                    if challenge is None:
                        action_result = {
                            "status": "ERROR", "errorCode": "challengeNeeded", "challengeNeeded": {
                                "type": "pinNeeded"}, "ids": [device['id']]}
                        response['commands'].append(action_result)

                        return response

                    elif not challenge.get('pin', False):
                        action_result = {
                            "status": "ERROR", "errorCode": "challengeNeeded", "challengeNeeded": {
                                "type": "userCancelled"}, "ids": [device['id']]}
                        response['commands'].append(action_result)

                        return response

                if acknowledge:
                    if challenge is None:
                        action_result = {
                            "status": "ERROR", "errorCode": "challengeNeeded", "challengeNeeded": {
                                "type": "ackNeeded"}, "ids": [device['id']]}
                        response['commands'].append(action_result)

                        return response
                try:    
                    states = trait.execute(
                            device, command, params, user_id, challenge)
                    states['online'] = True
                    action_result = {'ids': [device['id']], 'status': 'SUCCESS', 'states': states}
                    response['commands'].append(action_result)
                    
                except SmartHomeErrorNoChallenge as err:
                    action_failed = {'ids': [device['id']], 'status': 'ERROR', 'errorCode': err.code,
                                          'challengeNeeded': {'type': err.desc}}
                    logger.error(err)
                    response['commands'].append(action_failed)
                    return response
                except SmartHomeError as err:
                    action_failed = {'ids': [device['id']], 'status': 'ERROR', 'errorCode': err.code}
                    logger.error(err)
                    response['commands'].append(action_failed)
                    return response
                    

            if repstate.report_state_enabled():
                    if 'Doorbell' not in device['id'] and 'Camera' not in device['id']:
                        data = {'states': {device['id']: action_result['states']}}
                        self.statereport(requestId, user_id, data)

            # if "followUpToken" in params and 'DoorLock' in custom_data['domain']:
                # ndata = {'states':{},'notifications':{}}
                # ndata['states'][device_id] = action_result['states']
                # ndata['notifications'][device_id] = {'LockUnlock':{"priority": 0,"followUpResponse": {
                                            # "status": "SUCCESS", "followUpToken": params["followUpToken"], "isLocked":params['lock']}}}
                # statereport(result['requestId'], user_id, data)

        return response
