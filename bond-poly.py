#!/usr/bin/python3
"""
Polglot v2 NodeServer for Olibra Bond Bridge and controlled devices through local API
by Goose66 (W. Randy King) kingwrandy@gmail.com
"""
import sys
import re
from bondapi import *
import time
import polyinterface

# contstants for ISY Nodeserver interface
_ISY_BOOL_UOM =2 # Used for reporting status values for Controller and Bridge nodes
_ISY_PERCENT_UOM = 51 # For fan speed and light level, as a percentage
_ISY_ON_OFF_UOM = 78 # For non-dimmable light: 0-Off 100-On
_ISY_BARRIER_STATUS_UOM = 97 # For shades: 0-Closed, 100-Open, 101-Unknown, 102-Stopped, 103-Closing, 104–Opening
_ISY_RAW_UOM = 56 # Raw value form device UOM (speed and direction)
_ISY_INDEX_UOM = 25 # Custom index UOM for translating direction values
_IX_CFM_DIR_NA = 0
_IX_CFM_DIR_FORWARD = 1 # 1 for fan direction
_IX_CFM_DIR_REVERSE = 2 # -1 for fan direction

# custom parameter values for this nodeserver
_PARAM_HOSTNAMES = "hostname"
_PARAM_TOKENS = "token"

_LOGGER = polyinterface.LOGGER

# delay after calling API execDeviceAction() before calling getDeviceState() to avoid error (seconds)
_DELAY_AFTER_ACTION = 0.100 

# constants for type of light node (up light, down light, or default)
_LIGHT_TYPE_DEFAULT = 0
_LIGHT_TYPE_DOWN_LIGHT = 1
_LIGHT_TYPE_UP_LIGHT = 2

# action codes and property/state names for the different types of lights
_LIGHT_ACTION_ON = (API_ACTION_TURN_LIGHT_ON, API_ACTION_TURN_DOWN_LIGHT_ON, API_ACTION_TURN_UP_LIGHT_ON)
_LIGHT_ACTION_OFF = (API_ACTION_TURN_LIGHT_OFF, API_ACTION_TURN_DOWN_LIGHT_OFF, API_ACTION_TURN_UP_LIGHT_OFF)
_LIGHT_ACTION_SET_BRIGHTNESS = (API_ACTION_SET_BRIGHTNESS, API_ACTION_SET_DOWN_LIGHT_BRIGHTNESS, API_ACTION_SET_UP_LIGHT_BRIGHTNESS)
_LIGHT_ACTION_INC_BRIGHTNESS = (API_ACTION_INCREASE_BRIGHTNESS, API_ACTION_INCREASE_DOWN_LIGHT_BRIGHTNESS, API_ACTION_INCREASE_UP_LIGHT_BRIGHTNESS)
_LIGHT_ACTION_DEC_BRIGHTNESS = (API_ACTION_DECREASE_BRIGHTNESS, API_ACTION_DECREASE_DOWN_LIGHT_BRIGHTNESS, API_ACTION_DECREASE_UP_LIGHT_BRIGHTNESS)
_LIGHT_STATE_BRIGHTNESS = ("brightness", "down_light_brightness", "up_light_brightness")
_LIGHT_STATE_ENABLED = ("light", "down_light", "up_light")
_LIGHT_STATE_POWER = "light"

# Node for a celing fan
class CeilingFan(polyinterface.Node):

    id = "CEILING_FAN"
    hint = [0x01, 0x02, 0x01, 0x00] # Residential/Controller/Class A Motor Controller
    _deviceID = ""
    _maxSpeed = 0
    _hasDirection = 0
    
    def __init__(self, controller, primary, addr, name, deviceID=None, hasDirection=0):
        super(CeilingFan, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID and the maxSpeed from polyglot custom data
            cData = controller.getCustomData(addr).split(";")
            self._deviceID = cData[0]
            self._maxSpeed = int(cData[1])
            self._hasDirection = int(cData[2])

        else:
            self._deviceID = deviceID

            # get the properties of the fan
            respData = self.parent.bondBridge.getDeviceProperties(self._deviceID)
            self._maxSpeed = respData["max_speed"]
            self._hasDirection = hasDirection

            # store instance variables in polyglot custom data
            cData = ";".join([self._deviceID, str(self._maxSpeed), str(self._hasDirection)])
            controller.addCustomData(addr, cData)

    # Turn on the fan
    def cmd_don(self, command):

        _LOGGER.debug("Turn on fan in cmd_don: %s", str(command))

        # if a parameter (% speed) was specified, then use SetSpeed command to set the fan speed
        if command.get("value") is not None:
            
            # retrieve the parameter value for the command
            value = int(command.get("value"))

            # compute a speed value for the %
            speed = self.computeFanSpeed(value, self._maxSpeed)

            # Set the speed value for the fan (this turns the power on)
            if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_SET_SPEED, speed):
        
                # update state driver from the speed
                self.setDriver("ST", value)

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

        else:
            # execute the TurnOn action through the Bond bridge (to the previous speed)
            if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_ON):

                # Wait for some time before getting state to avoid errors
                time.sleep(_DELAY_AFTER_ACTION)

                # Get current speed
                respData = self.parent.bondBridge.getDeviceState(self._deviceID)
                state = self.computePercentSpeed(respData["speed"], self._maxSpeed)
    
                # update the state driver
                self.setDriver("ST", state)

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

    # Turn off the fan to the last speed
    def cmd_dof(self, command):

        _LOGGER.debug("Turn off fan in cmd_dof()...")

        # execute the TurnOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_OFF):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    # Increase fan speed by 1 speed 
    def cmd_increase_speed(self, command):

        _LOGGER.debug("Increase fan speed cmd_increase_speed()...")

        # execute the IncreaseSpeed action (by 1 speed) through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_INCREASE_SPEED, 1):

            # Wait for some time before getting state to avoid errors
            time.sleep(_DELAY_AFTER_ACTION)

            # Get current speed
            respData = self.parent.bondBridge.getDeviceState(self._deviceID)
            state = self.computePercentSpeed(respData["speed"], self._maxSpeed)
    
            # update the state driver
            self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in BRT command handler.")

    # Decrease fan speed by 1 speed
    def cmd_decrease_speed(self, command):

        _LOGGER.debug("Decrease fan speed cmd_decrease_speed()...")

        # execute the DecreaseSpeed action (by 1 speed) through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_DECREASE_SPEED, 1):

            # Wait for some time before getting state to avoid errors
            time.sleep(_DELAY_AFTER_ACTION)

            # Get current speed
            respData = self.parent.bondBridge.getDeviceState(self._deviceID)
            state = self.computePercentSpeed(respData["speed"], self._maxSpeed)
    
            # update the state driver
            self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DIM command handler.")

    # Change speed by speed value (allow fan speed to be set to known speed by user)
    def cmd_set_speed(self, command):

        _LOGGER.debug("Set fan speed cmd_set_speed: %s", str(command))

        # retrieve the speed value for the command
        query = command.get('query')
        speed = int(query.get("FAN_SPEED.uom56"))

        # If the speed value is greater than the max speed, then set to max speed
        if speed > self._maxSpeed:
            speed = self._maxSpeed
        
        # Set the speed value for the fan (this turns the power on)
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_SET_SPEED, speed):
        
            # Wait for some time before getting state to avoid errors
            time.sleep(_DELAY_AFTER_ACTION)

            # update state driver from the speed
            state = self.computePercentSpeed(speed, self._maxSpeed)
            self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in SET_SPEED command handler.")

    # Set fan direction
    def cmd_set_direction(self, command):

        _LOGGER.debug("Set fan direction in cmd_set_direction: %s", str(command))

        # ignore the command if the fan does not support set direction
        if self._hasDirection:

            # retrieve the integer value (%) for the command
            value = int(command.get("value"))

            # ignore the command if the 
            if value != _IX_CFM_DIR_NA:

                # translate value
                if value == _IX_CFM_DIR_REVERSE:
                    direction = -1
                else:
                    direction = 1

                # execute the SetDirection action through the Bond bridge
                if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_SET_DIRECTION, direction):
                
                    # update the state drvier
                    self.setDriver("GV0", value)

                else:
                    _LOGGER.warning("Call to exceDeviceAction() failed in SET_DIRECTION command handler.")

    def updateState(self, forceReport=False):
        
        _LOGGER.debug("Update fan driver values in updateState...")

        # check the fan status for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            if respData["power"] == 0:
                state = 0
            else:
                state = self.computePercentSpeed(respData["speed"], self._maxSpeed)

            if "direction" not in respData:
                direction = _IX_CFM_DIR_NA
            elif respData["direction"] == -1:
                direction = _IX_CFM_DIR_REVERSE
            else:
                direction = _IX_CFM_DIR_FORWARD

            # Update the fan node node states
            self.setDriver("ST", state, True, forceReport)
            self.setDriver("GV0", direction, True, forceReport)

        else:
            
            _LOGGER.warning("Call to getDeviceState() failed in updateState.")


    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_PERCENT_UOM},
        {"driver": "GV0", "value": 0, "uom": _ISY_INDEX_UOM},
    ]
    commands = {
        "DON": cmd_don,
        "DOF": cmd_dof,
        "BRT": cmd_increase_speed,
        "DIM": cmd_decrease_speed,
        "SET_SPEED": cmd_set_speed,
        "SET_DIRECTION": cmd_set_direction
    }

    # static method to compute percentage speed from fan speed value
    @staticmethod
    def computePercentSpeed(speed, maxSpeed):
        return  int(speed / maxSpeed * 100 + 0.5)

    # static method to compute fan speed value from percentage speed
    @staticmethod
    def computeFanSpeed(percent, maxSpeed):
        return  int(percent / 100 * (maxSpeed - 1) + 1)

# Node for a dimmable light attached to a ceiling fan (handled independently)
class Light(polyinterface.Node):

    id = "LIGHT"
    hint = [0x01, 0x02, 0x09, 0x00] # Residential/Controller/Dimmer
    _deviceID = ""
    _lightType = 0
    _hasOwnBrightness = 0
    
    def __init__(self, controller, primary, addr, name, deviceID=None, lightType=_LIGHT_TYPE_DEFAULT, hasOwnBrightness=0):
        super(Light, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID from polyglot custom data
            cData = controller.getCustomData(addr).split(";")
            self._deviceID = cData[0]
            self._lightType = int(cData[1])
            self._hasOwnBrightness = int(cData[2])

        else:
            self._deviceID = deviceID
            self._lightType = lightType
            self._hasOwnBrightness = hasOwnBrightness

            # store instance variables in polyglot custom data
            cData = ";".join([self._deviceID, str(self._lightType), str(self._hasOwnBrightness)])
            controller.addCustomData(addr, cData)

    # Turn on the light
    def cmd_don(self, command):

        _LOGGER.debug("Turn on light in cmd_don: %s", str(command))

        # if a parameter (% brightness) was specified, then use SetBrightness command
        if command.get("value") is not None:
            
            # retrieve the parameter value (%) for the command
            value = int(command.get("value"))
 
            # use the light specific action if supported
            if self._hasOwnBrightness:
                action = _LIGHT_ACTION_SET_BRIGHTNESS[self._lightType]
            else:
                action = _LIGHT_ACTION_SET_BRIGHTNESS[_LIGHT_TYPE_DEFAULT]

            if self.parent.bondBridge.execDeviceAction(self._deviceID, action, value):
        
                # update state driver to the brightness set
                self.setDriver("ST", value)

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

        else:

            # execute the TurnOn action through the Bond bridge (to the previous brightness)
            if self.parent.bondBridge.execDeviceAction(self._deviceID, _LIGHT_ACTION_ON[self._lightType]):

                # Wait for some time before getting state to avoid errors
                time.sleep(_DELAY_AFTER_ACTION)

                # update the node state
                self.updateState()

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")


    # Turn off the light
    def cmd_dof(self, command):

        _LOGGER.debug("Turn off light in cmd_dof: %s", str(command))

        # execute the TurnLightOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, _LIGHT_ACTION_OFF[self._lightType]):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    # Increase brightness by 15%
    def cmd_increase_brightness(self, command):

        _LOGGER.debug("Increase light brightness in cmd_increase_brightness()...")

        # use the light specific action if supported
        if self._hasOwnBrightness:
            action = _LIGHT_ACTION_INC_BRIGHTNESS[self._lightType]
        else:
            action = _LIGHT_ACTION_INC_BRIGHTNESS[_LIGHT_TYPE_DEFAULT]

        # execute the IncreaseBrightness action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, action, 15):

            # Wait for some time before getting state to avoid errors
            time.sleep(_DELAY_AFTER_ACTION)

            # update the node state
            self.updateState()

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in BRT command handler.")

    # Decrease brightness by 15%
    def cmd_decrease_brightness(self, command):

        _LOGGER.debug("Decrease light brightness in cmd_decrease_brightness()...")

        # use the light specific action if supported
        if self._hasOwnBrightness:
            action = _LIGHT_ACTION_DEC_BRIGHTNESS[self._lightType]
        else:
            action = _LIGHT_ACTION_DEC_BRIGHTNESS[_LIGHT_TYPE_DEFAULT]

        # execute the DecreaseBrightness action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, action, 15):

            # Wait for some time before getting state to avoid errors
            time.sleep(_DELAY_AFTER_ACTION)

            # update the node state
            self.updateState()

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DIM command handler.")

    def updateState(self, forceReport=False):
        
        _LOGGER.debug("Update light driver values in updateState...")
        
        # check the light state for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            if respData[_LIGHT_STATE_POWER] == 0 or respData[_LIGHT_STATE_ENABLED[self._lightType]] == 0:
                state = 0
            elif _LIGHT_STATE_BRIGHTNESS[self._lightType] in respData:
                state = int(respData[_LIGHT_STATE_BRIGHTNESS[self._lightType]])
            else:
                state = int(respData[_LIGHT_STATE_BRIGHTNESS[_LIGHT_TYPE_DEFAULT]])

            # Update the node states
            self.setDriver("ST", state, True, forceReport)

        else:
            _LOGGER.warning("Call to getDeviceState() failed in updateState.")

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_PERCENT_UOM}
    ]
    commands = {
        "DON": cmd_don,
        "DFON": cmd_don,
        "DOF": cmd_dof,
        "DFOF": cmd_dof,
        "BRT": cmd_increase_brightness,
        "DIM": cmd_decrease_brightness        
    }

# Node for a non-dimming light attached to a ceiling fan (handled independently)
class NoDimLight(polyinterface.Node):

    id = "NODIM_LIGHT" 
    hint = [0x01, 0x02, 0x10, 0x00] # Residential/Controller/Non-Dimming Light
    _deviceID = ""
    _lightType = 0
    
    def __init__(self, controller, primary, addr, name, deviceID=None, lightType=_LIGHT_TYPE_DEFAULT):
        super(NoDimLight, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID from polyglot custom data
            cData = controller.getCustomData(addr).split(";")
            self._deviceID = cData[0]
            self._lightType = int(cData[1])

        else:
            self._deviceID = deviceID
            self._lightType = lightType

            # store instance variables in polyglot custom data
            cData = ";".join([self._deviceID, str(self._lightType)])
            controller.addCustomData(addr, cData)

    # Turn on the light
    def cmd_don(self, command):

        _LOGGER.debug("Turn on light in cmd_don: %s", str(command))

        # execute the TurnLightOn action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, _LIGHT_ACTION_ON[self._lightType]):

           # update the state driver
            self.setDriver("ST", 100)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

    # Turn off the light
    def cmd_dof(self, command):

        _LOGGER.debug("Turn off light in cmd_dof: %s", str(command))

         # execute the TurnLightOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, _LIGHT_ACTION_OFF[self._lightType]):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    def updateState(self, forceReport=False):
        
        _LOGGER.debug("Update light driver values in updateState...")
        
        # check the light state for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            state = int(respData[_LIGHT_STATE_POWER] and respData[_LIGHT_STATE_ENABLED[self._lightType]]) * 100

            # Update the node states
            self.setDriver("ST", state, True, forceReport)

        else:
            
            _LOGGER.warning("Call to getDeviceState() failed in updateState.")

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_ON_OFF_UOM}
    ]
    commands = {
        "DON": cmd_don,
        "DFON": cmd_don,
        "DOF": cmd_dof,
        "DFOF": cmd_dof
    }

# Node for generic device
# Provides Power On and Off - a base for other device types
class Generic(polyinterface.Node):

    id = "GENERIC"
    hint = [0x01, 0x04, 0x02, 0x00] # Residential/Relay/On/Off Power Switch
    _deviceID = ""
    
    def __init__(self, controller, primary, addr, name, deviceID=None):
        super(Generic, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID from polyglot custom data
            self._deviceID = controller.getCustomData(addr)

        else:
            self._deviceID = deviceID

            # store instance variables in polyglot custom data
            controller.addCustomData(addr, self._deviceID)

    # Turn on device
    def cmd_don(self, command):

        _LOGGER.debug("Turn on device in cmd_don: %s", str(command))

        # execute the TurnOn action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_ON):

           # update the state driver
            self.setDriver("ST", 100)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

    # Turn off device
    def cmd_dof(self, command):

        _LOGGER.debug("Turn off device in cmd_dof()...")

         # execute the TurnOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_OFF):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    def updateState(self, forceReport=False):
        
        _LOGGER.debug("Update device driver values in updateState()...")
        
        # check the device state for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            state = int(respData["power"]) * 100

            # Update the node states
            self.setDriver("ST", state, True, forceReport)

        else:
            
            _LOGGER.warning("Call to getDeviceState() failed in updateState().")

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_ON_OFF_UOM}
    ]
    commands = {
        "DON": cmd_don,
        "DOF": cmd_dof
    }

# Node for fireplace device
# Currently just provides Power On and Off from Generic device
# Future functionality: Add separate node for fan, add commands to control flame (Dim/Bright)
class Fireplace(Generic):

    id = "FIREPLACE" 
   
# Node for shades
# Currently just provides Open and Close - does not try to parse actions and determine capabilities
# Future functionality: Add command for go to preset level
class Shade(Generic):

    id = "SHADE" 
    hint = [0x01, 0x04, 0x05, 0x00] # Residential/Relay/Open/Close Valve
    
  # Open shade
    def cmd_don(self, command):

        _LOGGER.debug("Open shade in cmd_don: %s", str(command))

        # execute the Open action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_OPEN):

           # update the state driver
            self.setDriver("ST", 100)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

    # Close shade
    def cmd_dof(self, command):

        _LOGGER.debug("Close shade in cmd_dof()...")

         # execute the Close action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_CLOSE):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    def updateState(self, forceReport=False):
        
        _LOGGER.debug("Update shade driver values in updateState()...")
        
        # check the device state for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            state = int(respData["open"]) * 100

            # Update the node states
            self.setDriver("ST", state, True, forceReport)

        else:
            
            _LOGGER.warning("Call to getDeviceState() failed in updateState().")

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_BARRIER_STATUS_UOM}
    ]
    commands = {
        "DON": cmd_don,
        "DOF": cmd_dof
    }
    
# Class for Bond Bridge or SBB composite device
class Bridge(polyinterface.Node):

    id = "BRIDGE"
    hint = [0x01, 0x0E, 0x01, 0x00] # Residential/Gateway
    bondBridge = None
    _bridgeHostName = ""
    _bridgeToken = ""

    def __init__(self, controller, primary, addr, name, bridgeHostName=None, bridgeToken=None):
        super(Bridge, self).__init__(controller, addr, addr, name) # send its own address as primary

        # make the receiver a primary node
        self.isPrimary = True

        if bridgeHostName is None:
        
            # retrieve instance variables from polyglot custom data
            cData = controller.getCustomData(addr).split(";")
            self._bridgeHostName = cData[0]
            self._bridgeToken = cData[1]

        else:
            self._bridgeHostName = bridgeHostName
            self._bridgeToken = bridgeToken

            # store instance variables in polyglot custom data
            cData = ";".join([self._bridgeHostName, self._bridgeToken])
            controller.addCustomData(addr, cData)
        
        # create an instance of the API object for the bridge with the specified hostname and token
        self.bondBridge = bondBridgeConnection(self._bridgeHostName, self._bridgeToken, _LOGGER)

     # Update node states for this and child nodes
    def cmd_query(self, command):

        _LOGGER.debug("Updating node states for bridge in cmd_query()...")
        
        # Update the node states for this bridge and force report of all driver values
        self.updateNodeStates(True)

    def discoverDevices(self):

        _LOGGER.debug("Discovering devices for bridge in discoverDevices()...")

        # get all devices from the bridge
        devices = self.bondBridge.getDeviceList()
        if devices is None:
            _LOGGER.warning("Bond bridge %s getDeviceList() returned no devices.", self.address)

        else:

            # iterate devices
            for devID in devices:
                device = devices[devID]

                # if the device ID is short (e.g., sequential numbers 1, 2, 3 for SBB devices, then append bridge ID to address)
                if len(devID) < 3:
                    devAddr = getValidNodeAddress(self.address[-8:] + "_" + devID)
                else:
                    devAddr = getValidNodeAddress(devID)
                
                _LOGGER.info("Discovered device - bridge: %s, addr: %s, name: %s, type: %s", self.address, devAddr, device["name"], device["type"])

                # If no node already exists for the device address, then add a node for the device
                if devAddr not in self.controller.nodes:

                    if device["type"] == API_DEVICE_TYPE_CEILING_FAN:
            
                        node = CeilingFan(
                            self.controller,
                            self.address,
                            devAddr,
                            getValidNodeName(device["name"]),
                            devID,
                            int(API_ACTION_SET_DIRECTION in device["actions"])
                            
                        )
                        self.controller.addNode(node)

                        # if the ceiling fan has a down light, add a separate node for the down light
                        if API_ACTION_TURN_DOWN_LIGHT_ON in device["actions"]:

                            # add a Light node for a dimmable light, or a NoDimLight node for a non-dimmable light
                            if API_ACTION_SET_BRIGHTNESS in device["actions"]:
                                node = Light(
                                    self.controller,
                                    self.address,
                                    devAddr + "_dlt",
                                    getValidNodeName(device["name"] + " Down Light"),
                                    devID,
                                    _LIGHT_TYPE_DOWN_LIGHT,
                                    int(API_ACTION_SET_DOWN_LIGHT_BRIGHTNESS in device["actions"])
                                )
                            else:
                                node = NoDimLight(
                                    self.controller,
                                    self.address,
                                    devAddr + "_dlt",
                                    getValidNodeName(device["name"] + " Down Light"),
                                    devID,
                                    _LIGHT_TYPE_DOWN_LIGHT
                                )
                            self.controller.addNode(node)

                        # if the ceiling fan has an up light, add a separate node for the up light
                        if API_ACTION_TURN_UP_LIGHT_ON in device["actions"]:

                            # add a Light node for a dimmable light, or a NoDimLight node for a non-dimmable light
                            if API_ACTION_SET_BRIGHTNESS in device["actions"]:
                                node = Light(
                                    self.controller,
                                    self.address,
                                    devAddr + "_ult",
                                    getValidNodeName(device["name"] + " Up Light"),
                                    devID,
                                    _LIGHT_TYPE_UP_LIGHT,
                                    int(API_ACTION_SET_UP_LIGHT_BRIGHTNESS in device["actions"])
                                )
                            else:
                                node = NoDimLight(
                                    self.controller,
                                    self.address,
                                    devAddr + "_ult",
                                    getValidNodeName(device["name"] + " Up Light"),
                                    devID,
                                    _LIGHT_TYPE_UP_LIGHT
                                )
                            self.controller.addNode(node)

                        # if the ceiling fan has no UpDownLight and just a default light, add a separate node for the light
                        if API_ACTION_TURN_UP_LIGHT_ON not in device["actions"] and API_ACTION_TURN_DOWN_LIGHT_ON not in device["actions"] and API_ACTION_TURN_LIGHT_ON in device["actions"]:

                            # add a Light node for a dimmable light, or a NoDimLight node for a non-dimmable light
                            if API_ACTION_SET_BRIGHTNESS in device["actions"]:
                                node = Light(
                                    self.controller,
                                    self.address,
                                    devAddr + "_lt",
                                    getValidNodeName(device["name"] + " Light"),
                                    devID,
                                    _LIGHT_TYPE_DEFAULT,
                                    int(True) 
                                )
                            else:
                                node = NoDimLight(
                                    self.controller,
                                    self.address,
                                    devAddr + "_lt",
                                    getValidNodeName(device["name"] + " Light"),
                                    devID,
                                    _LIGHT_TYPE_DEFAULT
                                )
                            self.controller.addNode(node)

                    elif device["type"] == API_DEVICE_TYPE_FIREPLACE:
                        node = Fireplace(
                            self.controller,
                            self.address,
                            devAddr,
                            getValidNodeName(device["name"]),
                            devID
                        )
                        self.controller.addNode(node)

                    elif device["type"] == API_DEVICE_MOTORIZED_SHADES:
                        node = Shade(
                            self.controller,
                            self.address,
                            devAddr,
                            getValidNodeName(device["name"]),
                            devID
                        )
                        self.controller.addNode(node)

                    elif device["type"] == API_DEVICE_GENERIC_DEVICE:
                        node = Generic(
                            self.controller,
                            self.address,
                            devAddr,
                            getValidNodeName(device["name"]),
                            devID
                        )
                        self.controller.addNode(node)

    # update the state of all nodes through the Bond bridge
    def updateNodeStates(self, forceReport=False):

        # Make sure the bridge is alive
        status = self.bondBridge.isBridgeAlive()
        
        if status:

            # Update the Bond connection driver value
            self.setDriver("ST", 1, True, forceReport)

            # iterate through the nodes of the nodeserver
            for addr in self.controller.nodes:
        
                # ignore the controller and this bridge node
                if addr != self.address and addr != self.controller.address:

                    # if the device belongs to this bridge (node's primary is this nodes address),
                    # then update the state of the nodes drivers
                    node = self.controller.nodes[addr] 
                    if node.primary == self.address:
                        node.updateState(forceReport)

        else:

            # Update the Bond connection driver value
            self.setDriver("ST", 0, True, forceReport)

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_BOOL_UOM}
    ]
    commands = {
        "QUERY": cmd_query
    }

# Controller class
class Controller(polyinterface.Controller):

    id = "CONTROLLER"
    _customData = {}

    def __init__(self, poly):
        super(Controller, self).__init__(poly)
        self.name = "Bond NodeServer"

    # Start the nodeserver
    def start(self):

        _LOGGER.info("Started Bond Bridge nodeServer...")

        # remove all existing notices for the nodeserver
        self.removeNoticesAll()

        # load custom data from polyglot
        self._customData = self.polyConfig["customData"]
            
        # load nodes previously saved to the polyglot database
        # Note: has to be done in two passes to ensure Bridge (primary/parent) nodes exist
        # before device nodes
        # first pass for BRIDGE nodes
        for addr in self._nodes:           
            node = self._nodes[addr]
            if node["node_def_id"] == "BRIDGE":
                
                _LOGGER.debug("Adding previously saved node - addr: %s, name: %s, type: %s", addr, node["name"], node["node_def_id"])
                self.addNode(Bridge(self, node["primary"], addr, node["name"]))

        # second pass for device nodes
        for addr in self._nodes:         
            node = self._nodes[addr]    
            if node["node_def_id"] not in ("CONTROLLER", "BRIDGE"):

                _LOGGER.debug("Adding previously saved node - addr: %s, name: %s, type: %s", addr, node["name"], node["node_def_id"])

                # add ceiling fan nodes and light nodes
                if node["node_def_id"] == "CEILING_FAN":
                    self.addNode(CeilingFan(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "NODIM_LIGHT":
                    self.addNode(NoDimLight(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "LIGHT":
                    self.addNode(Light(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "SHADE":
                    self.addNode(Shade(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "FIREPLACE":
                    self.addNode(Fireplace(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "GENERIC":
                    self.addNode(Generic(self, node["primary"], addr, node["name"]))

        # Set the nodeserver status flag to indicate nodeserver is running
        self.setDriver("ST", 1, True, True)

        # Set the log level to the currently set log level
        self.setDriver("GV20", _LOGGER.level, True, True)
 
        # update the driver values of all nodes (force report)
        self.updateNodeStates(True)

    # Run discovery for Sony devices
    def cmd_discover(self, command):

        _LOGGER.debug("Discover devices in cmd_discover()...")
        
        self.discover()

    # Update the profile on the ISY
    def cmd_updateProfile(self, command):

        _LOGGER.debug("Install profile in cmd_updateProfile()...")
        
        self.poly.installprofile()
        
    # Update the profile on the ISY
    def cmd_setLogLevel(self, command):

        _LOGGER.debug("Set logging level in cmd_setLogLevel(): %s", str(command))

        # retrieve the parameter value for the command
        value = int(command.get("value"))
 
        # set the current logging level
        _LOGGER.setLevel(value)

        # update the state driver to the level set
        self.setDriver("GV20", value)
        
    # called every longPoll seconds (default 30)
    def longPoll(self):

        pass

    # called every shortPoll seconds (default 10)
    def shortPoll(self):

        # update the driver values for all nodes
        self.updateNodeStates()

    # helper method for storing custom data
    def addCustomData(self, key, data):

        # add specififed data to custom data for specified key
        self._customData.update({key: data})

    # helper method for retrieve custom data
    def getCustomData(self, key):

        # return data from custom data for key
        return self._customData[key]

    # discover bridges and SBB devices
    def discover(self):

        self.removeNoticesAll()

        # create an empty array for the bridge list
        bridges = []
    
        # Check to see if host(s) and token(s) were specified in custom custom configuration parameters
        customParams = self.polyConfig["customParams"]
        if _PARAM_HOSTNAMES in customParams:
            
            # get lists of hosts and tokens from custom parameters
            hostNameList = customParams[_PARAM_HOSTNAMES]

            # iterate through bridges in controller's hostname list and build an array of bridges
            hosts = hostNameList.split(";")
            for host in hosts:

                bridges.append({"hostname": host})

                # if tokens are provided, get the corresponding token
                if _PARAM_TOKENS in customParams:
                
                    # get the corresponding token
                    tokenList = customParams[_PARAM_TOKENS]
                    token = tokenList.split(";")[hosts.index(host)]

                    # add the token to the just appended bridge item
                    bridges[-1]["token"] = token

            dynamicDiscovery = False

        else:

            # Discover Bond Bridges and SBB devices using mDNS
            bridges.extend(bondDiscoverBridges(5, _LOGGER))

            dynamicDiscovery = True

        # Process each discovered or specified bridge or SBB device
        for bridge in bridges:

            # better chance for success using IP address
            if "ipaddress" in bridge:
                host = bridge["ipaddress"]
            else:
                host = bridge["hostname"]

            # check for token
            if "token" in bridge:

                token = bridge["token"]

            else:

                # get token for host
                token = bondGetBridgeToken(host, _LOGGER)

                # check the returned token
                if token == API_TOKEN_FAILED: # general failure

                    # Log a warning and add a notice to Polyglot dashboard
                    _LOGGER.warning("Unable to connect to specified hostname %s", host)
                    self.addNotice("Unable to connect to Bond bridge at hostname {}. Please check the 'hostname' parameter value in the Custom Configuration Parameters and/or that the Bond bridge or device is reachable on your network from you Polyglot server before retrying.".format(host))

                    # move to the next bridge
                    continue

                elif token == API_TOKEN_LOCKED: # bond bridge locked

                    # Log a warning and add a notice to Polyglot dashboard
                    _LOGGER.warning("Token locked on bridge at hostname %s", host)
                    self.addNotice("Bond bridge or device at hostname {} is locked. Please unlock the Bond bridge or device before executing the Discover Devices command.".format(host))

                    # move to the next bridge
                    continue

            # get info for the bridge
            bridgeInfo = bondGetBridgeInfo(host, token, _LOGGER)

            # check the returned token
            if bridgeInfo == API_BRIDGE_INFO_FAILED: # general failure

                # Log a warning and add a notice to Polyglot dashboard
                _LOGGER.warning("Unable to connect to specified hostname %s", host)
                if dynamicDiscovery:
                    self.addNotice("Unable to connect to Bond bridge at hostname {} retrieved from mDNS. Please check that the Bond bridge or device is reachable on your network from your Polyglot server.".format(host))
                else:
                    self.addNotice("Unable to connect to Bond bridge at hostname {}. Please check the 'hostname' parameter value in the Custom Configuration Parameters and restart this nodeserver.".format(host))

                # move to the next bridge
                continue

            elif bridgeInfo == API_BRIDGE_INFO_BAD_TOKEN: # bond bridge locked

                # Log a warning and add a notice to Polyglot dashboard
                _LOGGER.warning("Aunthentication error (bad token) for bridge at hostname %s", host)
                if dynamicDiscovery:
                    self.addNotice("Unable to authenticate with the Bond bridge at hostname {} using the retrieved token. Consider specifying the hostname and token manually through Custom Configuration Parameters and try discovery again.".format(host))
                else:
                    self.addNotice("Unable to authenticate with the Bond bridge at hostname {} using the supplied token. Please check the corresponding 'token' parameter value in the Custom Configuration Parameters and restart this nodeserver.".format(host))

                # move to the next bridge
                continue

            else:

                # Older firmware may not return the bondid property, so use the one in the bridge list (or the last eight of the token)
                bridgeID = bridgeInfo.get("bondid", bridge.get("bondid", token[-8:]))

                # If the name is missing, just use the bridgeID
                bridgeName = bridgeInfo.get("name", bridgeID)

                # check to see if a bridge node already exists for the bridge
                bridgeAddr = getValidNodeAddress(bridgeID)
                if bridgeAddr not in self.nodes:

                    # create a Bridge node for the Bond Bridge
                    bridge = Bridge(self, self.address, bridgeAddr, getValidNodeName(bridgeName), host, token)
                    self.addNode(bridge)
                    
                else:
                    bridge = self.nodes[bridgeAddr]

                # perform device discovery for the bridge node
                bridge.discoverDevices()

        # send custom data added by new nodes to polyglot
        self.saveCustomData(self._customData)

        # update the driver values for the discovered bridges and devices (force report)
        self.updateNodeStates(True)

    # update the node states for all bridge and device nodes
    def updateNodeStates(self, forceReport=False):

        # iterate through the nodes of the nodeserver
        for addr in self.nodes:
        
            # ignore the controller node
            if addr != self.address:

                # if the device is a bridge node, call the updateNodeStates method
                node = self.controller.nodes[addr]
                if node.id == "BRIDGE":
                    node.updateNodeStates(forceReport)

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_BOOL_UOM},
        {"driver": "GV20", "value": 0, "uom": _ISY_INDEX_UOM}
    ]
    commands = {
        "DISCOVER": cmd_discover,
        "UPDATE_PROFILE" : cmd_updateProfile,
        "SET_LOGLEVEL": cmd_setLogLevel
    }

# Removes invalid charaters and lowercase ISY Node address
def getValidNodeAddress(s):

    # remove <>`~!@#$%^&*(){}[]?/\;:"' characters
    addr = re.sub(r"[.<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", s)


    return addr[:14].lower()

# Removes invalid charaters for ISY Node description
def getValidNodeName(s):

    # remove <>`~!@#$%^&*(){}[]?/\;:"' characters from names
    return re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", s)

# Main function to establish Polyglot connection
if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface()
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        _LOGGER.warning("Received interrupt or exit...")
        polyglot.stop()
    except Exception as err:
        _LOGGER.error('Excption: {0}'.format(err), exc_info=True)
        sys.exit(0)