import hashlib
import base64
import json

from modules.database import Settings
from modules.helpers import _tempConvert, SmartHomeError, SmartHomeErrorNoChallenge
from modules.domoticz import getDomoticzState, queryDomoticz


def query(custom_data, device, user_id):

    dbsettings = Settings.query.get_or_404(1)
    idx = custom_data['idx']
    domain = custom_data['domain']
    if domain in ['Group', 'Scene']:
        state = getDomoticzState(user_id, idx, 'scene')
    else:
        state = getDomoticzState(user_id, idx)

    response = {}

    if 'action.devices.traits.OnOff' in device['traits']:
        if domain in ['Group', 'Scene']:
            data = state['Status'] != 'Off'
            response['on'] = data
        else:
            data = state['Data'] != 'Off'
            response['on'] = data

    if 'action.devices.traits.OpenClose' in device['traits']:
        if domain in ['BlindsPercentage', 'BlindsStop']:
            response['openPercent'] = state['Level']
        elif state['Data'] == 'Open':
            response['openPercent'] = 100
        else:
            response['openPercent'] = 0

    if 'action.devices.traits.LockUnlock' in device['traits']:
        data = state['Data'] != 'Unlocked'
        response['isLocked'] = data

    if 'action.devices.traits.StartStop' in device['traits']:
        if domain in ['VenetianBlindsUS', 'VenetianBlindsEU', 'BlindsStop']:
            response['isRunning'] = True

    if 'action.devices.traits.Brightness' in device['traits']:
        response['brightness'] = int(state['Level'] * 100 / state['MaxDimLevel'])

    if 'action.devices.traits.ColorSetting' in device['traits']:
        try:
            color_rgb = json.loads(state['Color'])
            if color_rgb is not None:
                # Convert RGB to decimal
                color_decimal = color_rgb["r"] * 65536 + color_rgb["g"] * 256 + color_rgb["b"]

                response['color'] = {'spectrumRGB': color_decimal}

                if color_rgb["m"] == 2:
                    colorTemp = (color_rgb["t"] * (255 / 100)) * 10
                    response['color'] = {'temperatureK': round(colorTemp)}

        except ValueError:
            response = {}

    if 'action.devices.traits.TemperatureSetting' in device['traits']:
        if domain in ['Thermostat', 'Setpoint']:
            if 'actual_temp_idx' in custom_data:
                actual_temp_idx = getDomoticzState(user_id, custom_data['actual_temp_idx'])
                current_temp = float(actual_temp_idx['Temp'])
            else:
                current_temp = float(state['Data'])
            response['thermostatTemperatureAmbient'] = round(_tempConvert(current_temp, dbsettings.tempunit), 1)
            setpoint = float(state['SetPoint'])
            response['thermostatTemperatureSetpoint'] = round(_tempConvert(setpoint, dbsettings.tempunit), 1)
            if 'selector_modes_idx' in custom_data:
                selectorModesState = getDomoticzState(user_id, custom_data['selector_modes_idx'])
                selectorLevel = selectorModesState['Level']
                selectorModes = base64.b64decode(selectorModesState['LevelNames']).decode('UTF-8').lower().split("|")
                modeIndex = int(selectorLevel / 10)
                response['thermostatMode'] = selectorModes[modeIndex]
            else:
                response['thermostatMode'] = 'heat'
        elif domain in ['Temp', 'TempHumidity', 'TempHumidityBaro']:
            current_temp = float(state['Temp'])
            if round(_tempConvert(current_temp, dbsettings.tempunit), 1) <= 3:
                response['thermostatMode'] = 'cool'
            else:
                response['thermostatMode'] = 'heat'
            response['thermostatTemperatureAmbient'] = round(_tempConvert(current_temp, dbsettings.tempunit), 1)
            response['thermostatTemperatureSetpoint'] = round(_tempConvert(current_temp, dbsettings.tempunit), 1)
            if domain != 'Temp':
                current_humidity = state['Humidity']
                if current_humidity is not None:
                    response['thermostatHumidityAmbient'] = current_humidity

    if 'action.devices.traits.TemperatureControl' in device['traits']:
        if domain in ['Temp', 'TempHumidity', 'TempHumidityBaro']:
            current_temp = float(state['Temp'])
            response['temperatureAmbientCelsius'] = round(_tempConvert(current_temp, dbsettings.tempunit), 1)

    if 'action.devices.traits.Toggles' in device['traits']:
        levelName = base64.b64decode(state.get("LevelNames")).decode('UTF-8').split("|")
        level = state['Level']
        index = int(level / 10)

        toggle_settings = {
            levelName[index]: state['Data'] != 'Off'
            }

        if toggle_settings:
            response["currentToggleSettings"] = toggle_settings

    if 'action.devices.traits.SensorState' in device['traits']:
        if state['Data'] is not None:
            response['currentSensorStateData'] = [{'name': 'SmokeLevel', 'currentSensorState': (
                                                    'smoke detekted' if state['Data'] == 'On' else 'no smoke detected')}]

    if 'action.devices.traits.OccupancySensing' in device['traits']:
        if state['Data'] is not None:
            response['occupancy'] = ('OCCUPIED' if state['Data'] == 'On' else 'UNOCCUPIED')

    if 'action.devices.traits.ArmDisarm' in device['traits']:

        response["isArmed"] = state['Data'] != "Normal"
        if response["isArmed"]:
            response["currentArmLevel"] = state['Data']
            
    if 'action.devices.traits.EnergyStorage' in device['traits']:
        if state['BatteryLevel'] != 255:
            battery = state['BatteryLevel']
            if battery is not None:
                if battery == 100:
                    descriptive_capacity_remaining = "FULL"
                elif 50 <= battery < 100:
                    descriptive_capacity_remaining = "HIGH"
                elif 15 <= battery < 50:
                    descriptive_capacity_remaining = "MEDIUM"
                elif 10 <= battery < 15:
                    descriptive_capacity_remaining = "LOW"
                elif 0 <= battery < 10:
                    descriptive_capacity_remaining = "CRITICALLY_LOW"
                    
                response['descriptiveCapacityRemaining'] = descriptive_capacity_remaining
                response['capacityRemaining'] = [{
                    'unit': 'PERCENTAGE',
                    'rawValue': battery
                }]
            

    response['online'] = True
    if domain not in ['Group', 'Scene'] and state['BatteryLevel'] != 255:
        if state['BatteryLevel'] <= 10: # Report low battery below 10%
            response['exceptionCode'] = 'lowBattery'

    return response


def execute(device, command, params, user_id, challenge):

    custom_data = device['customData']
    idx = device['customData']['idx']
    domain = device['customData']['domain']

    if domain in ['Group', 'Scene']:
        state = getDomoticzState(user_id, idx, 'scene')
    else:
        state = getDomoticzState(user_id, idx)

    response = {}
    url = '?type=command&param='

    if command == "action.devices.commands.OnOff":

        if domain in ['Group', 'Scene']:
            url += 'switchscene&idx=' + idx + '&switchcmd=' + (
                        'On' if params['on'] else 'Off')
        else:
            url += 'switchlight&idx=' + idx + '&switchcmd=' + (
                        'On' if params['on'] else 'Off')

        response['on'] = params['on']

    if command == 'action.devices.commands.LockUnlock':
        if domain in ['DoorLockInverted']:
            url += 'switchlight&idx=' + idx + '&switchcmd=' + (
                            'Off' if params['lock'] else 'On')
        else:
            url += 'switchlight&idx=' + idx + '&switchcmd=' + (
                            'On' if params['lock'] else 'Off')

        response['isLocked'] = params['lock']

    if command == "action.devices.commands.ActivateScene":

        if params['deactivate'] is False:
            url += 'switchscene&idx=' + idx + '&switchcmd=On'

    if command == "action.devices.commands.BrightnessAbsolute":

        url += 'switchlight&idx=' + idx + '&switchcmd=Set%20Level&level=' + str(
            int(params['brightness'] * state['MaxDimLevel'] / 100))

        response['brightness'] = params['brightness']

    if command == "action.devices.commands.ColorAbsolute":

        if "temperature" in params["color"]:
            tempRange = 1700 - 6500
            kelvinTemp = params['color']['temperature']
            setTemp = 100 - (((kelvinTemp - 1700) / tempRange) * 100)

            url += 'setkelvinlevel&idx=' + idx + '&kelvin=' + str(
                round(setTemp))

        elif "spectrumRGB" in params["color"]:
            # Convert decimal to hex
            setcolor = params['color']
            color_hex = hex(setcolor['spectrumRGB'])[2:]
            lost_zeros = 6 - len(color_hex)
            color_hex_str = ""
            for x in range(lost_zeros):
                color_hex_str += "0"
            color_hex_str += str(color_hex)

            url += 'setcolbrightnessvalue&idx=' + idx + '&hex=' + color_hex_str

        response['color'] = params['color']

    if command == 'action.devices.commands.ThermostatTemperatureSetpoint':

        url += 'setsetpoint&idx=' + idx + '&setpoint=' + str(
                    params['thermostatTemperatureSetpoint'])

        response['thermostatTemperatureSetpoint'] = params['thermostatTemperatureSetpoint']

    if command == 'action.devices.commands.ThermostatSetMode':

        if 'selector_modes_idx' in custom_data:
            data = getDomoticzState(user_id, custom_data['selector_modes_idx'])
            selctorModeLevels = base64.b64decode(data["LevelNames"]).decode('UTF-8').split("|")
            selctorModeNames = [x.lower() for x in selctorModeLevels]

            if params['thermostatMode'] in selctorModeNames:
                thermostatMode = str(selctorModeNames.index(params['thermostatMode']) * 10)

                url += 'switchlight&idx=' + custom_data['selector_modes_idx'] + '&switchcmd=Set%20Level&level=' + thermostatMode

    if command == 'action.devices.commands.OpenClose':

        if domain in ['BlindsPercentage', 'BlindsStop']:
            url += 'switchlight&idx=' + idx + '&switchcmd=Set%20Level&level=' + str(
                params['openPercent'])

        else:
            p = params.get('openPercent', 50)
            url += 'switchlight&idx=' + idx + '&switchcmd='
            if p == 100:
                url += 'Open'
            if p == 0:
                url += 'Close'

        response['openState'] = [{'openPercent': params['openPercent']}]

    if command == 'action.devices.commands.StartStop':

        if params['start'] is False:
            url += 'switchlight&idx=' + idx + '&switchcmd=Stop'
        else:
            url += 'switchlight&idx=' + idx + '&switchcmd=' + (
                    'On' if params['start'] else 'Off')

    if command == 'action.devices.commands.GetCameraStream':

        if custom_data['camurl']:
            response['cameraStreamAccessUrl'] = custom_data['camurl']
            response['online'] = True
            return response
        else:
            raise SmartHomeError('streamUnavailable',
                             'Unable to execute {} for {}'.format(command, device['id']))

    if command == 'action.devices.commands.ArmDisarm':

        if params["arm"]:
            if params["armLevel"] == "Arm Home":
                url += "setsecstatus&secstatus=1"
            if params["armLevel"] == "Arm Away":
                url += "setsecstatus&secstatus=2"
        else:
            url += "setsecstatus&secstatus=0"

        url += '&seccode=' + hashlib.md5(str.encode(challenge.get('pin'))).hexdigest()

        response['isArmed'] = params['arm']
        if response["isArmed"]:
            response['currentArmLevel'] = params['armLevel']

    if command == 'action.devices.commands.SetToggles':

        levelName = base64.b64decode(state.get("LevelNames")).decode('UTF-8').split("|")

        for key in params['updateToggleSettings']:
            key = key.replace("_", " ")
            if key in levelName:
                slevel = str(levelName.index(key) * 10)

            url += 'switchlight&idx=' + idx + '&switchcmd=Set%20Level&level=' + slevel

    if state['Protected'] is True:
        url = url + '&passcode=' + challenge.get('pin')

    r = queryDomoticz(user_id, url)

    result = json.loads(r)
    status = result.get('status')

    if status == 'ERR':
        raise SmartHomeError('functionNotSupported',
                             'Unable to execute {} for {}'.format(command, device['id']))
    elif status == 'ERROR':
        raise SmartHomeErrorNoChallenge('challengeNeeded', 'challengeFailedPinNeeded',
                                        'Unable to execute {} for {} - challenge needed '.format(command, device['id']))

    return response
