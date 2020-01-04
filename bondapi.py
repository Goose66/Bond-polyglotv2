#!/usr/bin/env python
"""
Python wrapper class for Bond Bridge local API
by Goose66 (W. Randy King) kingwrandy@gmail.com
"""

import sys
import logging
import requests
import json

# Bond Local REST API v2.9 spec.
_API_ENDPOINT = "http://{host_name}{path}"
_API_GET_DEVICE_LIST = {
    "path": "/v2/devices",
    "method": "GET"
}
_API_GET_DEVICE_INFO = {
    "path": "/v2/devices/{device_id}",
    "method": "GET"
}
_API_GET_DEVICE_PROPERTIES = {
    "path": "/v2/devices/{device_id}/properties",
    "method": "GET"
}
_API_GET_DEVICE_STATE = {
    "path": "/v2/devices/{device_id}/state",
    "method": "GET"
}
_API_DEVICE_ACTION = {
    "path": "/v2/devices/{device_id}/actions/{action_id}",
    "method": "PUT"
}
_API_BRIDGE_REBOOT = {
    "path": "/v2/sys/reboot",
    "method": "PUT"
}
_API_GET_BRIDGE_VERSION = {
    "path": "/v2/sys/version",
    "method": "GET"
}

# Device actions
API_ACTION_TURN_ON = "TurnOn"
API_ACTION_TURN_OFF = "TurnOff"
API_ACTION_TOGGLE_POWER = "TogglePower"
API_ACTION_SET_TIMER = "SetTimer" # argument: (int) seconds
API_ACTION_SET_SPEED = "SetSpeed" # argument: (int) speed
API_ACTION_INCREASE_SPEED = "IncreaseSpeed" #argument: (int) num of speeds
API_ACTION_DECREASE_SPEED = "DecreaseSpeed" #argument: (int) num of speeds
API_ACTION_BREEZE_ON = "BreezeOn"
API_ACTION_BREEZE_ON = "BreezeOff"
API_ACTION_BREEZE_ON = "SetBreeze"  #argument: (array) [mode, mean, var]
API_ACTION_SET_DIRECTION = "SetDirection" # argument: (int) 1 = forward, -1 = reverse
API_ACTION_TOGGLE_DIRECTION = "ToggleDirection"
API_ACTION_TURN_LIGHT_ON = "TurnLightOn"
API_ACTION_TURN_LIGHT_OFF = "TurnLightOff"
API_ACTION_TOGGLE_LIGHT = "ToggleLight"
API_ACTION_TURN_UP_LIGHT_ON = "TurnUpLightOn"
API_ACTION_TURN_DOWN_LIGHT_ON = "TurnDownLightOn"
API_ACTION_TURN_UP_LIGHT_OFF = "TurnUpLightOff"
API_ACTION_TURN_DOWN_LIGHT_OFF = "TurnDownLightOff"
API_ACTION_TOGGLE_UP_LIGHT = "ToggleUpLight"
API_ACTION_TOGGLE_DOWN_LIGHT = "ToggleDownLight"
API_ACTION_SET_BRIGHTNESS = "SetBrightness" # argument: (int) brightness percentage
API_ACTION_INCREASE_BRIGHTNESS = "IncreaseBrightness" # argument: (int) amount increase percentage
API_ACTION_DECREASE_BRIGHTNESS = "DecreaseBrightness" # argument: (int) amount decrease percentage
API_ACTION_SET_UP_LIGHT_BRIGHTNESS = "SetUpLightBrightness" # argument: (int) brightness percentage
API_ACTION_SET_DOWN_LIGHT_BRIGHTNESS = "SetDownLightBrightness" # argument: (int) brightness percentage
API_ACTION_INCREASE_UP_LIGHT_BRIGHTNESS = "IncreaseUpLightBrightness" # argument: (int) amount increase percentage
API_ACTION_INCREASE_DOWN_LIGHT_BRIGHTNESS = "IncreaseDownLightBrightness" # argument: (int) amount increase percentage
API_ACTION_DECREASE_UP_LIGHT_BRIGHTNESS = "DecreaseUpLightBrightness" # argument: (int) amount decrease percentage
API_ACTION_DECREASE_DOWN_LIGHT_BRIGHTNESS = "DecreaseDownLightBrightness" # argument: (int) amount decrease percentage
API_ACTION_SET_FLAME = "SetFlame" # argument: (int) flame percentage
API_ACTION_INCREASE_FLAME = "IncreaseFlame" # argument: (int) flame percentage increase
API_ACTION_DECREASE_FLAME = "DecreaseFlame" # argument: (int) flame percentage decrease
API_ACTION_OPEN = "Open"
API_ACTION_CLOSE = "Close"
API_ACTION_TOGGLE_OPEN = "ToggleOpen"
API_ACTION_TURN_FP_FAN_OFF = "TurnFpFanOff"
API_ACTION_TURN_FP_FAN_ON = "TurnFpFanOn"
API_ACTION_SET_FP_FAN = "SetFpFan"

# Device types
API_DEVICE_TYPE_CEILING_FAN = "CF"
API_DEVICE_TYPE_FIREPLACE = "FP"
API_DEVICE_MOTORIZED_SHADES = "MS"
API_DEVICE_GENERIC_DEVICE = "GX"

# Timeout duration for HTTP calls - defined here for easy tweaking
_HTTP_TIMEOUT = 6.05

# interface class
class BondAPI(object):

    # Primary constructor method
    def __init__(self, hostName, token, logger=None):

        if logger is None:
            # setup basic console logger for debugging
            logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
            self._logger = logging.getLogger() # Root logger
        else:
            self._logger = logger

        # declare instance variables
        self._hostName = hostName
        self._token = token

        # open an HTTP session
        self._bridgeSession = requests.Session()

    # Call the specified REST API
    def _call_api(self, api, deviceID = None, action = None, arg = None):

        self._logger.debug("in _call_api()...")

        if arg:
            payload = {"argument": arg}
        else:
            payload = {}
        
        method = api["method"]
        path = api["path"].format(device_id = deviceID, action_id = action) 

        # uncomment the next line to dump POST data to log file for debugging
        #self._logger.debug("HTTP %s data: %s", method + " " + path, payload)

        try:
            response = self._bridgeSession.request(method,
                _API_ENDPOINT.format(
                    host_name = self._hostName,
                    path = path
                ),
                data = json.dumps(payload), # because REST API requires double quotes on parameter names
                headers = {"BOND-Token": self._token}, # same every call     
                timeout=_HTTP_TIMEOUT
            )
            
            # Need to be able to pass 404 errors for unsupported commands and
            # 401 errors for bad token - for now just raise HTTP errors to be
            # handled in exception handling
            response.raise_for_status()    

        # Allow timeout and connection errors to be ignored - log and return false
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            self._logger.warning("HTTP %s in _call_api() failed: %s", method, str(e))
            return False
        except:
            self._logger.error("Unexpected error occured: %s", sys.exc_info()[0])
            raise

        return response

    # Get a list of the devices (fans, fireplaces, motorized shades, generic) setup in the Bond bridge or device
    # with device info for populating device lists
    # combines calls to device list and device info to build list
    def getDeviceList(self):
        """Returns list of devices setup in the bond bridge."""

        # get the device list
        response  = self._call_api(_API_GET_DEVICE_LIST)
        
        # pass through connection errors (none)
        if not response:
            return None
        
        # otherwise get the device IDs from the response data
        elif int(response.headers["content-length"]) > 0:

            respData = response.json()
            deviceList = {}

            # iterate through key IDs
            for deviceID in respData.keys():

                if deviceID != "_":

                    # get the device info
                    response = self._call_api(_API_GET_DEVICE_INFO, deviceID)
                    devInfo = response.json()

                    # add the device as an item to the device list dict
                    deviceList.update({deviceID: devInfo})

        return deviceList

    # Get properties of device
    def getDeviceProperties(self, deviceID):
        """Returns dictionary of properties for the device."""

        response = self._call_api(_API_GET_DEVICE_PROPERTIES, deviceID)
        
        # pass through connection errors (false)
        if not response:
            return False
        
        # otherwise return the properties dictionary from the response data
        elif int(response.headers["content-length"]) > 0:

            respData = response.json()
            return respData

    # Get state of device
    def getDeviceState(self, deviceID):
        """Returns dictionary of state variables for the device."""

        response = self._call_api(_API_GET_DEVICE_STATE, deviceID)
        
        # pass through connection errors (false)
        if not response:
            return False
        
        # otherwise return the state vars dictionary from the response data
        elif int(response.headers["content-length"]) > 0:

            respData = response.json()
            return respData
       
    # Execute a device action
    def execDeviceAction(self, deviceID, action, argument = None):
        """Executes the specified action for the device."""

        return self._call_api(_API_DEVICE_ACTION, deviceID, action, argument)    

    # Get bridge information
    def getBridgeInfo(self):
        """Returns dictionary of properties for version information about hardware and firmware."""

        response = self._call_api(_API_GET_BRIDGE_VERSION)

        # pass through connection errors (false)
        if not response:
            return False
        
        # otherwise return the properties dictionary from the response data
        elif int(response.headers["content-length"]) > 0:

            respData = response.json()
            return respData

    # Ping the bridge to see if it is connected
    def isBridgeAlive(self):
        """Pings the Bond bridge to ensure it is responding."""

        return (self._call_api(_API_GET_BRIDGE_VERSION) != False)   

