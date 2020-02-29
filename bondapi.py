#!/usr/bin/env python
"""
Python wrapper class for Bond Bridge local API
by Goose66 (W. Randy King) kingwrandy@gmail.com
"""

import sys
import logging
import requests
import json
from zeroconf import ServiceBrowser, Zeroconf
import ipaddress
import time

# Configure a module level logger for module testing
_LOGGER = logging.getLogger(__name__)
#logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)

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
_API_GET_BRIDGE_TOKEN = {
    "path": "/v2/token",
    "method": "GET"
}
_API_GET_BRIDGE_INFO = {
    "path": "/v2/bridge",
    "method": "GET"
}

# Service type for Zeroconf
_BOND_SERVICE_TYPE = "_bond._tcp.local."

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

# API return codes constants
API_TOKEN_LOCKED = "locked"
API_TOKEN_FAILED = "error"

API_BRIDGE_INFO_BAD_TOKEN = "auth_failure"
API_BRIDGE_INFO_FAILED = "error"

# Timeout duration for HTTP calls - defined here for easy tweaking
_HTTP_TIMEOUT = 6.05

# interface class for a particular Bond Bridge or SBB device
class bondBridgeConnection(object):

    # Primary constructor method
    def __init__(self, hostName, token, logger=_LOGGER):

        self._logger = logger

        # declare instance variables
        self._hostName = hostName
        self._token = token

        # open an HTTP session
        self._bridgeSession = requests.Session()

    # Call the specified REST API
    def _call_api(self, api, deviceID=None, action=None, arg=None):

        if arg:
            payload = {"argument": arg}
        else:
            payload = {}
        
        method = api["method"]
        path = api["path"].format(device_id = deviceID, action_id = action) 

        # uncomment the next line to dump HTTP request data to log file for debugging
        #self._loggerdebug("HTTP %s data: %s", method + " " + path, payload)

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
            
            # May want to add special handling for 404 errors for unsupported commands and 401 errors for bad token
            # For now just raise all HTTP errors to be handled in exception handling
            response.raise_for_status()

        # Allow timeout and connection errors to be ignored - log and return false
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
            self._logger.warning("HTTP %s in _call_api() failed: %s", method, str(e))
            return False
        except:
            self._logger.error("Unexpected error occured: %s", sys.exc_info()[0])
            raise

        # uncomment the next line to dump HTTP response to log file for debugging
        #self._loggerdebug("HTTP response code: %d data: %s", response.status_code, response.text)

        return response

    # Get a list of the devices (fans, fireplaces, motorized shades, generic) setup in the Bond bridge or device
    # with device info for populating device lists
    # combines calls to device list and device info to build list
    def getDeviceList(self):
        """Returns list of devices setup in the bond bridge."""

        self._logger.debug("in API getDeviceList()...")

        # get the device list
        response  = self._call_api(_API_GET_DEVICE_LIST)
        
        # if data returned, get the device IDs from the response data
        if response and int(response.headers["content-length"]) > 0:

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

        # otherwise return error (False)
        else:
            return False

    # Get properties of device
    def getDeviceProperties(self, deviceID):
        """Returns dictionary of properties for the device."""

        self._logger.debug("in API getDeviceProperties()...")

        response = self._call_api(_API_GET_DEVICE_PROPERTIES, deviceID)
        
        # if response data was returned, then return the properties dictionary from the response data
        if response and int(response.headers["content-length"]) > 0:

            respData = response.json()
            return respData

        # otherwise return error (false)
        else:
            return False

    # Get state of device
    def getDeviceState(self, deviceID):
        """Returns dictionary of state variables for the device."""

        self._logger.debug("in API getDeviceState()...")

        response = self._call_api(_API_GET_DEVICE_STATE, deviceID)
        
        # if response data was returned, then return the state vars dictionary from the response data
        if response and int(response.headers["content-length"]) > 0:

            respData = response.json()
            return respData

        # otherwise return error (false)
        else:
            return False
       
    # Execute a device action
    def execDeviceAction(self, deviceID, action, argument = None):
        """Executes the specified action for the device."""
        
        self._logger.debug("in API execDeviceAction()...")

        # Call the API with the specified action and device ID
        response = self._call_api(_API_DEVICE_ACTION, deviceID, action, argument)

        # If a good code was returned, then return True
        if response and response.status_code == 204:
            return True

        # Otherwise, return False
        else:
            return False

    # Get bridge information
    def getBridgeInfo(self):
        """Returns dictionary of properties for the bridge."""

        self._logger.debug("in API getBridgeInfo()...")

        # Get the version information for the bridge
        response = self._call_api(_API_GET_BRIDGE_VERSION)

        # If a response was returned and it has contents
        if response and int(response.headers["content-length"]) > 0:

            # Get the bridge properties dictionary from the response data
            bridgeInfo = response.json()

            # Get the name of the bridge.
            # Note this API is not in the v2 documentation, so it may go away
            response = self._call_api(_API_GET_BRIDGE_INFO)
            if response and int(response.headers["content-length"]) > 0:

                # add the name property from the response to the return data
                respData = response.json()
                if "name" in respData.keys():
                    bridgeInfo["name"] = respData["name"]
                
            return bridgeInfo

        # otherwise return error (False)
        else:
            return False

    # Ping the bridge to see if it is connected
    def isBridgeAlive(self):
        """Pings a Bond bridge to ensure it is responding."""

        return (self._call_api(_API_GET_BRIDGE_VERSION) != False)   

    # Close the session (prevents resource warnings when the class is released)
    def close(self):
        self._bridgeSession.close()

def bondGetBridgeInfo(hostName, token, logger=_LOGGER):
    """Make authenticated call to retrieve the Bridge/SBB Device info - for external calling

    Parameters:
    hostName -- host name or IP address of Bond bridge or SBB device
    token -- authentication token
    Returns:
    dictionary of properties for the bridge or return code (API_BRIDGE_INFO_BAD_TOKEN, API_BRIDGE_INFO_FAILED)
    """

    logger.debug("in bondGetBridgeInfo()...")

    try:
        # Call the REST API to get the bridge version info
        response = requests.request(_API_GET_BRIDGE_VERSION["method"],
            _API_ENDPOINT.format(
                host_name = hostName,
                path = _API_GET_BRIDGE_VERSION["path"]
            ),
            headers = {"BOND-Token": token},
            timeout=_HTTP_TIMEOUT
        )       
        
        # raise anything other than a successful (200) HTTP code to error handling
        response.raise_for_status()

        # Get the bridge properties dictionary from the response data
        bridgeInfo = response.json()
   
        # if the device is a bridge node (rather than a SBB device), call the REST API to get the bridge name
        if bridgeInfo["target"] in ("zermatt", "snowbird"):
            response = requests.request(_API_GET_BRIDGE_INFO["method"],
                _API_ENDPOINT.format(
                    host_name = hostName,
                    path = _API_GET_BRIDGE_INFO["path"]
                ),
                headers = {"BOND-Token": token},
                timeout=_HTTP_TIMEOUT
            )

            if response.status_code == 401:
                return API_BRIDGE_INFO_BAD_TOKEN
            else:
                # raise anything other than a success (200) or authentication error (401) to error handling
                response.raise_for_status()

            # add the name property from the info response
            respData = response.json()
            if "name" in respData.keys():
                bridgeInfo["name"] = respData["name"]

        # otherwise, for SBB devices, call the device list REST API to test the token
        else:
            response = requests.request(_API_GET_DEVICE_LIST["method"],
                _API_ENDPOINT.format(
                    host_name = hostName,
                    path = _API_GET_DEVICE_LIST["path"]
                ),
                headers = {"BOND-Token": token},
                timeout=_HTTP_TIMEOUT
            )
            
            if response.status_code == 401:
                return API_BRIDGE_INFO_BAD_TOKEN
            else:
                # raise anything other than a success (200) or authentication error (401) to error handling
                response.raise_for_status()

        return bridgeInfo
 
    # For errors that may indicate a bad hostName, log a warning and return false
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        logger.warning("HTTP GET failed in bondGetBridgeInfo() failed: %s", str(e))
        return API_BRIDGE_INFO_FAILED
    except:
        logger.exception("Unexpected error from HTTP call in bondGetBridgeInfo(): %s", sys.exc_info()[0])
        raise

def bondGetBridgeToken(hostName, logger=_LOGGER):
    """Attempts to retrieve token for Bridge/SBB Device - for external calling

    Parameters:
    hostName -- host name or IP address of Bond bridge or SBB device
    Returns:
    Token or return code (API_TOKEN_LOCKED, API_TOKEN_FAILED)
    """

    logger.debug("in bondGetBridgeToken()...")

    # Call the REST API to get the token
    try:
        response = requests.request(_API_GET_BRIDGE_TOKEN["method"],
            _API_ENDPOINT.format(
                host_name = hostName,
                path = _API_GET_BRIDGE_TOKEN["path"]
            ),
            timeout=_HTTP_TIMEOUT
        )       
        
        # raise anything other than a successful (200) HTTP code to error handling
        response.raise_for_status()

        # check to see if the bridge is unlocked
        respData = response.json()
        if respData["locked"] == 0:
        
            # return the token
            return respData["token"]

        else:
        
            # return indicator that bridge was locked
            return API_TOKEN_LOCKED

    # For errors that may indicate a bad hostName, log a warning and return false
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as e:
        logger.warning("HTTP GET in bondGetBridgeToken() failed: %s", str(e))
        return API_TOKEN_FAILED
    except:
        logger.exception("Unexpected error from HTTP call in bondGetBridgeToken(): %s", sys.exc_info()[0])
        raise

def bondDiscoverBridges(timeout=5, logger=_LOGGER):
    """Discover Bond Bridges and Smart By Bond devices using mDNS service discover

    Parameters:
    timeout -- timeout for mDNS discovery (Avahi Browse) (defaults to 5 seconds)
    Returns:
    Array of dictionaries, one for each bridge or SBB device discovered
    """
    # class for service listener
    class serviceListener:

        bridges = []

        def remove_service(self, zeroconf, type, name):
            pass

        def add_service(self, zeroconf, type, name):
            info = zeroconf.get_service_info(type, name)

            # uncomment the next line to dump info for the service
            #logger.debug("Service %s added, service info: %s", name, info)

            bridgeDescriptor = {"bondid": info.get_name(), "hostname": info.server.rstrip("."), "ipaddress":str(ipaddress.IPv4Address(info.addresses[0]))}
            logger.info("Bond Bridge/device discovered: %s", str(bridgeDescriptor))

            self.bridges.append(bridgeDescriptor)

    logger.debug("in API bondDiscoverBridges()...")

    # creaate Zeroconf instance and listener for service discovery
    zeroconf = Zeroconf()
    listener = serviceListener()

    # browse for Bond Bridges and SBB devices
    browser = ServiceBrowser(zeroconf, _BOND_SERVICE_TYPE, listener)

    # wait the specified time for response(s)
    time.sleep(timeout)
    browser.cancel()

    # close the Zeroconf instance to release threads and resources
    zeroconf.close()

    return listener.bridges