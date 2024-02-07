# -*- coding: utf-8 -*-

import requests
import base64
import json
import os
import re
import modules.config as config

from modules.database import User, Settings
from modules.helpers import logger

aogDevs = {}


class AogState:
    def __init__(self):
        self.id = ''
        self.type = ''
        self.traits = []
        self.name = {}
        self.willReportState = True
        self.attributes = {}
        self.customData = {}


def getDomain(device):
    
    if device["Type"] in ['Color Switch', 'Group', 'Scene', 'Temp', 'Thermostat', 'Setpoint', 'Temp + Humidity', 'Temp + Humidity + Baro', 'Security']:
        devs = device["Type"].replace(" ", "")
        devs = devs.replace("+", "")
        return devs
    elif device["Type"] in ['Light/Switch', 'Lighting 1', 'Lighting 2', 'Lighting 3', 'Lighting 4', 'Lighting 5', 'RFY', 'Value']:
        if device["Type"] == 'Value' and device.get('SwitchType') is None:
            return None
        devs = device.get('SwitchType')
        devs = devs.replace(" ", "")
        devs = devs.replace("/", "")
        devs = devs.replace("+", "")

        return devs

    return None

    if device['Type'] == 'Value' and device['SwitchType'] is None:
        return None

    return None


def getDesc(user_id, device):
    user = User.query.filter_by(username=user_id).first()

    if device.id in user.device_config:
        desc = user.device_config[device.id]
        return desc
    else:
        return None


# Get additional settings from domoticz description in <voicecontrol> </voicecontrol>tags
def getDeviceConfig(descstr):
    ISLIST = ['nicknames']
    rawconfig = re.findall(r'<voicecontrol>(.*?)</voicecontrol>', descstr, re.DOTALL)
    if len(rawconfig) > 0:
        try:
            lines = rawconfig[0].strip().splitlines()
            cfgdict = {}
            for line in lines:
                assign = line.split('=')
                varname = assign[0].strip().lower()
                if varname != "":
                    if varname in ISLIST:
                        allvalues = assign[1].split(',')
                        varvalues = []
                        for val in allvalues:
                            varvalues.append(val.strip())
                        cfgdict[varname] = varvalues
                    else:
                        varvalue = assign[1].strip()
                        if varvalue.lower() == "true":
                            varvalue = True
                        elif varvalue.lower() == "false":
                            varvalue = False
                        cfgdict[varname] = varvalue
        except Exception:
            logger.error('Error parsing device configuration from Domoticz device description:', rawconfig[0])
            return None

        return cfgdict
    return None


def getAog(device, user_id=None):

    dbsettings = Settings.query.get_or_404(1)
    domain = getDomain(device)
    minThreehold = -20
    maxThreehold = 40
    if domain is None:
        return None

    aog = AogState()
    aog.id = domain + "_" + device.get('idx')
    aog.name = {
        'name': device.get('Name'),
        'nicknames': []
        }
    if device.get('Type') in ['Light/Switch', 'Color Switch', 'Lighting 1', 'Lighting 2', 'Lighting 3','Lighting 4', 'Lighting 5', 'RFY', 'Value']:
        aog.type = 'action.devices.types.LIGHT'
    if device.get('Image') == 'WallSocket':
        aog.type = 'action.devices.types.OUTLET'
    if device.get('Image') in ['Generic', 'Phone']:
        aog.type = 'action.devices.types.SWITCH'
    if device.get('Image') == 'Fan':
        aog.type = 'action.devices.types.FAN'
    if device.get('Image') == 'Heating':
        aog.type = 'action.devices.types.HEATER'
        
    if domain in ['Temp', 'TempHumidity', 'TempHumidityBaro', 'DoorContact', 'Contact']:
        aog.type = 'action.devices.types.SENSOR'
    if domain in ['Thermostat', 'Setpoint']:
        aog.type = 'action.devices.types.THERMOSTAT'
    if domain in ['VenetianBlindsUS', 'VenetianBlindsEU', 'Blinds', 'BlindsStop', 'BlindsPercentage']:
        aog.type = 'action.devices.types.BLINDS'
    if domain in ['Selector']:
        aog.type = 'action.devices.types.SWITCH'
    if domain in ['DoorLock', 'DoorLockInverted']:
        aog.type = 'action.devices.types.LOCK'
    
    aog.customData['check_state'] = True
    # Try to get device specific voice control configuration from Domoticz
    aog.customData['dzTags'] = False
    desc = getDesc(user_id, aog)
    if desc is None:
        desc = getDeviceConfig(device.get("Description"))
        if desc is not None:
            logger.debug('<voicecontrol> tags found for idx %s in domoticz description.', aog.id)
            aog.customData['dzTags'] = True

    if desc is not None:
        n = desc.get('nicknames', None)
        if n is not None:
            aog.name['nicknames'].extend(n)
        r = desc.get('room', None)
        if r is not None:
            aog.roomHint = r
        ack = desc.get('ack', False)
        if ack:
            aog.customData['acknowledge'] = ack
        chkState = desc.get('check_state', True)
        if not chkState:
            aog.customData['check_state'] = chkState
        repState = desc.get('report_state', True)
        if not repState:
            aog.willReportState = repState
        st = desc.get('devicetype', None)
        if st is not None and st.lower() in config.TYPES:
            aog.type = 'action.devices.types.' + st.upper()
        if domain in ['Thermostat', 'Setpoint']:
            minT = desc.get('minThreehold', None)
            if minT is not None:
                minThreehold = minT
            maxT = desc.get('maxThreehold', None)
            if maxT is not None:
                maxThreehold = maxT
            temp_idx = desc.get('actual_temp_idx', None)
            if temp_idx is not None:
                aog.customData['actual_temp_idx'] = temp_idx
            modes_idx = desc.get('selector_modes_idx', None)
            if modes_idx is not None:
                aog.customData['selector_modes_idx'] = modes_idx
        if domain in ['Doorbell', 'Camera']:
            camurl = desc.get('camurl', None)
            if camurl:
                aog.customData['camurl'] = camurl
        hide = desc.get('hide', False)
        if hide:
            domain = domain + '_Hidden'

    aog.customData['idx'] = device.get('idx')
    aog.customData['domain'] = domain
    aog.customData['protected'] = device.get('Protected')
    aog.notificationSupportedByAgent = (True if domain in ['SmokeDetector', 'Doorbell', 'DoorLock', 'DoorLockInverted'] else False)       

    if domain == 'Scene':
        aog.type = 'action.devices.types.SCENE'
        aog.traits.append('action.devices.traits.Scene')
    if domain == 'Security':
        aog.type = 'action.devices.types.SECURITYSYSTEM'
        aog.traits.append('action.devices.traits.ArmDisarm')
        aog.customData['protected'] = True
        aog.attributes = {
            "availableArmLevels": {
                "levels": [{
                    "level_name": "Arm Home",
                    "level_values": [
                        {"level_synonym": ["armed home", "low security", "home and guarding", "level 1", "home", "SL1"],
                            "lang": "en"},
                        {"level_synonym": dbsettings.armlevels['armhome'],
                            "lang": dbsettings.language}
                    ]
                }, {
                    "level_name": "Arm Away",
                    "level_values": [
                        {"level_synonym": ["armed away", "high security", "away and guarding", "level 2", "away", "SL2"],
                            "lang": "en"},
                        {"level_synonym": dbsettings.armlevels['armaway'],
                            "lang": dbsettings.language}
                    ]
                }],
                "ordered": True
                }
            }
    if domain == 'Group':
        aog.type = 'action.devices.types.SWITCH'
        aog.traits.append('action.devices.traits.OnOff')

    if domain == 'SmokeDetector':
        aog.type = 'action.devices.types.SMOKE_DETECTOR'
        aog.traits.append('action.devices.traits.SensorState')
        aog.attributes = {'sensorStatesSupported': [
                            {'name': 'SmokeLevel',
                             'descriptiveCapabilities': {
                                'availableStates': [
                                    'smoke detected',
                                    'no smoke detected']
                                }
                            }
                        ]
                    }
    if domain in ['OnOff', 'Dimmer', 'PushOnButton', 'PushOffButton']:
        aog.traits.append('action.devices.traits.OnOff')
    if domain == 'Dimmer':
        aog.traits.append('action.devices.traits.Brightness')
    if domain in ['DoorLock', 'DoorLockInverted']:
        aog.traits.append('action.devices.traits.LockUnlock')

    if domain in ['VenetianBlindsUS', 'VenetianBlindsEU', 'Blinds', 'BlindsStop', 'BlindsPercentage']:
        aog.traits.append('action.devices.traits.OpenClose')
        if domain in ['VenetianBlindsUS', 'VenetianBlindsEU', 'BlindsStop']:
            aog.traits.append('action.devices.traits.StartStop')
        if domain in ['VenetianBlindsUS', 'VenetianBlindsEU', 'Blinds']:
            aog.attributes = {'discreteOnlyOpenClose': True}

    if domain == 'ColorSwitch':
        aog.traits.append('action.devices.traits.OnOff')
        aog.traits.append('action.devices.traits.Brightness')
        aog.traits.append('action.devices.traits.ColorSetting')
        aog.attributes = {'colorModel': 'rgb',
                          'colorTemperatureRange': {
                                'temperatureMinK': 1700,
                                'temperatureMaxK': 6500}
                        }
    if domain == 'Selector':
        aog.traits.append('action.devices.traits.OnOff')
        aog.traits.append('action.devices.traits.Toggles')
        levelName = base64.b64decode(device.get("LevelNames")).decode('UTF-8').split("|")
        levels = []
        if levelName:
            for s in levelName:
                levels.append(
                    {
                        "name": s.replace(" ", "_"),
                        "name_values": [
                            {"name_synonym": [s],
                             "lang": "en"},
                            {"name_synonym": [s],
                             "lang": dbsettings.language},
                        ],
                    }
                )
        aog.attributes = {'availableToggles': levels}

    # Modes trait for selector not working yet -->
    if domain == 'Selector_modes':
        aog.type = 'action.devices.types.SWITCH'
        aog.traits.append('action.devices.traits.Modes')
        levelName = base64.b64decode(device.get("LevelNames")).decode('UTF-8').split("|")
        levels = []
        if levelName:
            for s in levelName:
                levels.append(
                    {
                        "name": s.replace(" ", "_"),
                        "name_values": [
                            {"name_synonym": [s],
                             "lang": "en"},
                            {"name_synonym": [s],
                             "lang": dbsettings.language},
                        ],
                        "settings": {
                            "setting_name": s.replace(" ", "_"),
                            "setting_values": [
                                {"setting_synonym": [s],
                                 "lang": "en"},
                                {"setting_synonym": [s],
                                 "lang": dbsettings.language},
                            ]
                        }
                    }
                )
        aog.attributes = {'availableModes': levels}
        # <-- Modes trait for selector not working yet

    if domain in ['Temp', 'TempHumidity', 'TempHumidityBaro']:
        aog.traits.append('action.devices.traits.TemperatureSetting')
        aog.attributes = {'thermostatTemperatureUnit': dbsettings.tempunit,
                          'thermostatTemperatureRange': {
                            'minThresholdCelsius': -30,
                            'maxThresholdCelsius': 40},
                          'queryOnlyTemperatureSetting': True,
                          'availableThermostatModes': ['heat', 'cool'],
                        }
    if domain in ['Thermostat', 'Setpoint']:
        aog.traits.append('action.devices.traits.TemperatureSetting')
        aog.attributes = {'thermostatTemperatureUnit': dbsettings.tempunit,
                          'thermostatTemperatureRange': {
                            'minThresholdCelsius': minThreehold,
                            'maxThresholdCelsius': maxThreehold},
                          'availableThermostatModes':  ['heat', 'cool'],
                        }
        if 'selector_modes_idx' in aog.customData:
            data = getDomoticzState(user_id, aog.customData['selector_modes_idx'])
            selectorModes = base64.b64decode(data['LevelNames']).decode('UTF-8').lower().split("|")
            aog.attributes['availableThermostatModes'] = selectorModes

    if domain == 'MotionSensor':
        aog.type = 'action.devices.types.SENSOR'
        aog.traits.append('action.devices.traits.OccupancySensing')
        aog.attributes = {"occupancySensorConfiguration": [{
                            "occupancySensorType": "PIR",
                            }]}
    if domain in ['DoorContact', 'Contact']:
        aog.traits.append('action.devices.traits.OpenClose')
        aog.attributes = {'discreteOnlyOpenClose': True,
                          'queryOnlyOpenClose': True}
    if domain in ['Doorbell', 'Camera']:
        aog.type = 'action.devices.types.CAMERA'
        if domain == 'Doorbell':
            aog.type = 'action.devices.types.DOORBELL'
            aog.traits.append('action.devices.traits.ObjectDetection')
        aog.traits.append('action.devices.traits.CameraStream')
        aog.attributes = {
            'cameraStreamSupportedProtocols': [
                "hls",
                "dash",
                "smooth_stream",
                "progressive_mp4"
            ],
            'cameraStreamNeedAuthToken': False
        }
    
    batteryLevel = device.get('BatteryLevel')
    if domain not in ['Group', 'Scene'] and batteryLevel != 255:
        aog.traits.append('action.devices.traits.EnergyStorage')
        aog.attributes['queryOnlyEnergyStorage'] = True
        aog.attributes['isRechargeable'] = False

    return aog


# Save device info in json format
def saveJson(user_id, data):

    datafile = user_id + "_devices.json"
    filename = os.path.join(config.DEVICES_DIRECTORY, datafile)

    with open(filename, 'w') as fp:
        json.dump(data, fp,  default=lambda o: o.__dict__,
                    indent=4, ensure_ascii=False)

    logger.info('Devices is saved in ' + datafile + ' in ' + config.DEVICES_DIRECTORY + ' folder')


def queryDomoticz(username, url):

    user = User.query.filter_by(username=username).first()
    domourl = user.domo_url
    domoCredits = (user.domouser, user.domopass)

    try:
        r = requests.get(domourl + '/json.htm' + url,
                         auth=domoCredits, timeout=5.00)
    except Exception:
        return "{}"

    return r.text


def getDomoticzDevices(user_id):

    user = User.query.filter_by(username=user_id).first()
    aogDevs.clear()

    try:
        r = json.loads(queryDomoticz(user_id, '?type=command&param=getdevices&plan=' + user.roomplan + '&filter=all&used=true'))
    except Exception:
        logger.error("Error connection to domoticz!")
        saveJson(user_id, aogDevs)
        return

    devs = r['result']

    for d in devs:
        aog = getAog(d, user_id)
        if aog is None:
            continue

        aogDevs[aog.id] = aog

    logger.info('Retreiving devices from domoticz')
    saveJson(user_id, aogDevs)


def getDomoticzState(user_id, idx, device='id'):

    if 'id' in device:
        url = '?type=command&param=getdevices&rid=' + idx
    elif 'scene' in device:
        url = '?type=command&param=getscenes&rid=' + idx
    r = json.loads(queryDomoticz(user_id, url))
    devs = r['result']
    for d in devs:
        data = d

    return data
