#!/usr/bin/python3
"""
Polglot v2 NodeServer for Olibra Bond Bridge and controlled devices through local API
by Goose66 (W. Randy King) kingwrandy@gmail.com
"""
import sys
import re
from bondapi import *
import polyinterface

_ISY_BOOL_UOM =2 # Used for reporting status values for Controller and Bridge nodes
_ISY_PERCENT_UOM = 51 # For fan speed and light level, as a percentage
_ISY_ON_OFF_UOM = 78 # For non-dimmable light: 0-Off 100-On
_ISY_RAW_UOM = 56 # Raw value form device UOM (speed and direction)
_ISY_INDEX_UOM = 25 # Custom index UOM for translating direction values
_IX_CFM_DIR_FORWARD = 0 # 1 for fan direction
_IX_CFM_DIR_REVERSE = 1 # -1 for fan direction

_PARAM_HOSTNAMES = "hostname"
_PARAM_TOKENS = "token"

_LOGGER = polyinterface.LOGGER

# Node for a celing fan
class CeilingFan(polyinterface.Node):

    id = "CEILING_FAN"
    hint = [0x01, 0x02, 0x01, 0x00] # Residential/Controller/Class A Motor Controller
    _deviceID = ""
    _maxSpeed = 0
    
    def __init__(self, controller, primary, addr, name, deviceID=None):
        super(CeilingFan, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID and the maxSpeed from polyglot custom data
            cData = controller.getCustomData(addr).split(";")
            self._deviceID = cData[0]
            self._maxSpeed = int(cData[1])

        else:
            self._deviceID = deviceID

            # get the max speed value for the fan
            respData = self.parent.bondBridge.getDeviceProperties(self._deviceID)
            self._maxSpeed = respData["max_speed"]

            # store instance variables in polyglot custom data
            cData = ";".join([self._deviceID, str(self._maxSpeed)])
            controller.addCustomData(addr, cData)

    # Turn on the fan
    def cmd_don(self, command):

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

                # Get current speed
                respData = self.parent.bondBridge.getDeviceState(self._deviceID)
                state = self.computePercentSpeed(respData["speed"], self._maxSpeed)
    
                # update the state driver
                self.setDriver("ST", state)

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

    # Turn off the fan to the last speed
    def cmd_dof(self, command):

         # execute the TurnOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_OFF):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    # Increase fan speed by 1 speed 
    def cmd_increase_speed(self, command):

        # execute the IncreaseSpeed action (by 1 speed) through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_INCREASE_SPEED, 1):

            # Get current speed
            respData = self.parent.bondBridge.getDeviceState(self._deviceID)
            state = self.computePercentSpeed(respData["speed"], self._maxSpeed)
    
            # update the state driver
            self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in BRT command handler.")

    # Decrease fan speed by 1 speed
    def cmd_decrease_speed(self, command):

        # execute the DecreaseSpeed action (by 1 speed) through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_DECREASE_SPEED, 1):

            # Get current speed
            respData = self.parent.bondBridge.getDeviceState(self._deviceID)
            state = self.computePercentSpeed(respData["speed"], self._maxSpeed)
    
            # update the state driver
            self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DIM command handler.")

    # Change speed by speed value (allow fan speed to be set to known speed by user)
    def cmd_set_speed(self, command):

        # retrieve the speed value for the command
        query = command.get('query')
        speed = int(query.get("FAN_SPEED.uom56"))

        # If the speed value is greater than the max speed, then set to max speed
        if speed > self._maxSpeed:
            speed = self._maxSpeed
        
        # Set the speed value for the fan (this turns the power on)
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_SET_SPEED, speed):
        
            # update state driver from the speed
            state = self.computePercentSpeed(speed, self._maxSpeed)
            self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in SET_SPEED command handler.")

    # Set fan direction
    def cmd_set_direction(self, command):

        # retrieve the integer value (%) for the command
        value = int(command.get("value"))

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
        
        # check the fan status for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            if respData["power"] == 0:
                state = 0
            else:
                state = self.computePercentSpeed(respData["speed"], self._maxSpeed)

            if respData["direction"] == -1:
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

# Node for a non-dimming light attached to a ceiling fan (handled independently)
class Light(polyinterface.Node):

    id = "LIGHT"
    hint = [0x01, 0x02, 0x09, 0x00] # Residential/Controller/Dimmer
    _deviceID = ""
    
    def __init__(self, controller, primary, addr, name, deviceID=None):
        super(Light, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        # Note: this is for future functionality of multiple bond bridges
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID from polyglot custom data
            self._deviceID = controller.getCustomData(addr)

        else:
            self._deviceID = deviceID

            # store instance variables in polyglot custom data
            controller.addCustomData(addr, self._deviceID)

    # Turn on the light
    def cmd_don(self, command):

        # if a parameter (% brightness) was specified, then use SetBrightness command
        if command.get("value") is not None:
            
            # retrieve the parameter value (%) for the command
            value = int(command.get("value"))
 
            # Set the brightness of the light
            if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_SET_BRIGHTNESS, value):
        
                # update state driver from the speed
                self.setDriver("ST", value)

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

        else:

            # execute the TurnOn action through the Bond bridge (to the previous brightness)
            if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_LIGHT_ON):

                # Get current brightness
                respData = self.parent.bondBridge.getDeviceState(self._deviceID)
                if respData:
                    state = int(respData["brightness"])

                    # update the state driver
                    self.setDriver("ST", state)

            else:
                _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")


    # Turn off the light
    def cmd_dof(self, command):

         # execute the TurnLightOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_LIGHT_OFF):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    # Increase brightness by 15%
    def cmd_increase_brightness(self, command):

        # execute the IncreaseBrightness action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_INCREASE_BRIGHTNESS, 15):

            # Get current brightness
            respData = self.parent.bondBridge.getDeviceState(self._deviceID)
            if respData:
                state = int(respData["brightness"])

                # update the state driver
                self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in BRT command handler.")

    # Decrease brightness by 15%
    def cmd_decrease_brightness(self, command):

        # execute the DecreaseBrightness action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_DECREASE_BRIGHTNESS, 15):

            # Get current brightness
            respData = self.parent.bondBridge.getDeviceState(self._deviceID)
            if respData:
                state = int(respData["brightness"])

                # update the state driver
                self.setDriver("ST", state)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DIM command handler.")

    def updateState(self, forceReport=False):
        
        # check the light state for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            if respData["light"] == 0:
                state = 0
            else:
                state = int(respData["brightness"])

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
    
    def __init__(self, controller, primary, addr, name, deviceID=None):
        super(NoDimLight, self).__init__(controller, primary, addr, name)
    
        # override the parent node with the bridge node (defaults to controller)
        # Note: this is for future functionality of multiple bond bridges
        self.parent = self.controller.nodes[self.primary]

        if deviceID is None:

            # retrieve the deviceID from polyglot custom data
            self._deviceID = controller.getCustomData(addr)

        else:
            self._deviceID = deviceID

            # store instance variables in polyglot custom data
            controller.addCustomData(addr, self._deviceID)

    # Turn on the light
    def cmd_don(self, command):

        # execute the TurnLightOn action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_LIGHT_ON):

           # update the state driver
            self.setDriver("ST", 100)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DON command handler.")

    # Turn off the light
    def cmd_dof(self, command):

         # execute the TurnLightOff action through the Bond bridge
        if self.parent.bondBridge.execDeviceAction(self._deviceID, API_ACTION_TURN_LIGHT_OFF):

            # update the state drvier
            self.setDriver("ST", 0)

        else:
            _LOGGER.warning("Call to exceDeviceAction() failed in DOF command handler.")

    def updateState(self, forceReport=False):
        
        # check the light state for the device on the Bond bridge
        respData = self.parent.bondBridge.getDeviceState(self._deviceID)

        if respData:

            state = int(respData["light"] * 100)

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

# Class for Bond Bridge
class Bridge(polyinterface.Node):

    id = "BRIDGE"
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
        self.bondBridge = BondAPI(self._bridgeHostName, self._bridgeToken, _LOGGER)

     # Update node states for this and child nodes
    def cmd_query(self, command):

        _LOGGER.debug("Updating node states in cmd_query()...")
        
        # Update the node states for this bridge and force report of all driver values
        self.updateNodeStates(True)

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
    _hostNameList = ""
    _tokenList = ""

    def __init__(self, poly):
        super(Controller, self).__init__(poly)
        self.name = "Bond Bridge NodeServer"

    # Start the nodeserver
    def start(self):

        _LOGGER.info("Started Bond Bridge NodeServer...")

        # remove all existing notices for the nodeserver
        self.removeNoticesAll()

        # load custom data from polyglot
        self._customData = self.polyConfig["customData"]

        # get Bond bridge connection info from custom configuration parameters
        try:
            customParams = self.polyConfig["customParams"]
            self._hostNameList = customParams[_PARAM_HOSTNAMES]
            self._tokenList = customParams[_PARAM_TOKENS]
        except KeyError:
            _LOGGER.error("Missing hostname(s) and/or token(s) in configuration.")
            self.addNotice("Please add 'hostname' and 'token' parameter values to the Custom Configuration Parameters and restart this nodeserver.")
            #self.poly.stop() # shutdown the nodeserver
            raise

        # load nodes previously saved to the polyglot database
        for addr in self._nodes:
            
            # ignore controller node
            if addr != self.address:
                
                node = self._nodes[addr]
                _LOGGER.debug("Adding previously saved node - addr: %s, name: %s, type: %s", addr, node["name"], node["node_def_id"])
        
                # add bridge nodes
                if node["node_def_id"] == "BRIDGE":
                    self.addNode(Bridge(self, node["primary"], addr, node["name"]))

                # add ceiling fan nodes and light nodes
                elif node["node_def_id"] == "CEILING_FAN":
                    self.addNode(CeilingFan(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "NODIM_LIGHT":
                    self.addNode(NoDimLight(self, node["primary"], addr, node["name"]))
                elif node["node_def_id"] == "LIGHT":
                    self.addNode(Light(self, node["primary"], addr, node["name"]))
            
        # Set the nodeserver status flag to indicate nodeserver is running
        self.setDriver("ST", 1, True, True)
 
        # iterate through the nodes of the nodeserver
        for addr in self.nodes:
        
            # ignore the controller node
            if addr != self.address:

                # if the device is a bridge node, call the updateNodeStates method
                node = self.controller.nodes[addr]
                if node.id == "BRIDGE":
                    node.updateNodeStates(True)

    # Run discovery for Sony devices
    def cmd_discover(self, command):

        _LOGGER.debug("Discovering devices in cmd_discover()...")
        
        self.discover()

    # Update the profile on the ISY
    def cmd_updateProfile(self, command):

        _LOGGER.debug("Installing profile in cmd_update_profile()...")
        
        self.poly.installprofile()
        
    # called every longPoll seconds (default 30)
    def longPoll(self):

        pass

    # called every shortPoll seconds (default 10)
    def shortPoll(self):

        # iterate through the nodes of the nodeserver
        for addr in self.nodes:
        
            # ignore the controller node
            if addr != self.address:

                # if the device is a bridge node, call the updateNodeStates method
                node = self.controller.nodes[addr]
                if node.id == "BRIDGE":
                    node.updateNodeStates(False)

    # helper method for storing custom data
    def addCustomData(self, key, data):

        # add specififed data to custom data for specified key
        self._customData.update({key: data})

    # helper method for retrieve custom data
    def getCustomData(self, key):

        # return data from custom data for key
        return self._customData[key]

    # discover bridges and controlled devices and build nodes
    def discover(self):

        # iterate through bridges in controller's hostname list
        # Note: to be replaced with some kind of Bond Bridge discovery routine (but have to be on the same LAN)
        hosts = self._hostNameList.split(";")
        for host in hosts:

            # get the corresponding token
            token = self._tokenList.split(";")[hosts.index(host)]

            # create a temporary API objet to communicate with the Bond Bridge
            tmpAPI = BondAPI(host, token, _LOGGER)

            # ping the Bond Bridge to see if it is alive and get bridge info
            respData = tmpAPI.getBridgeInfo()
            if respData:

                # check to see if a bridge node already exists
                bridgeAddr = getValidNodeAddress(respData["bondid"])
                if bridgeAddr not in self.nodes:

                    # create a Bridge node for the Bond Bridge
                    bridge = Bridge(self, self.address, bridgeAddr, getValidNodeName(respData["bondid"]), host, token)
                    self.addNode(bridge)
                    
                else:
                    bridge = self.nodes[bridgeAddr]
                
                # get devices from the bridge (just use the temporary API object)
                devices = tmpAPI.getDeviceList()
                if devices is None:
                    _LOGGER.warning("Bond bridge %s getDeviceList() returned no devices.", bridge.address)

                else:

                    # iterate devices
                    for devID in devices:
                        device = devices[devID]
                        devAddr = getValidNodeAddress(devID)
                        _LOGGER.debug("Discovered device - bridge: %s, addr: %s, name: %s, type: %s", bridge.address, devAddr, device["name"], device["type"])

                        if device["type"] == API_DEVICE_TYPE_CEILING_FAN:
                            
                            # If no node already exists for the device, then add a node for the device
                            if devAddr not in self.nodes:
                        
                                node = CeilingFan(
                                    self,
                                    bridge.address,
                                    devAddr,
                                    getValidNodeName(device["name"]),
                                    devID
                                )
                                self.addNode(node)

                                # if the ceiling fan has a light, add a separate node for the light
                                if API_ACTION_TURN_LIGHT_ON in device["actions"]:

                                    # add a Light node for a dimmable light, or a NoDimLight node for a non-dimmable light
                                    if API_ACTION_SET_BRIGHTNESS in device["actions"]:
                                        node = Light(
                                            self,
                                            bridge.address,
                                            devAddr + "_lt",
                                            getValidNodeName(device["name"] + " Light"),
                                            devID
                                        )
                                    else:
                                        node = NoDimLight(
                                            self,
                                            bridge.address,
                                            devAddr + "_lt",
                                            getValidNodeName(device["name"] + " Light"),
                                            devID
                                        )
                                    self.addNode(node)

                        elif device["type"] == API_DEVICE_TYPE_FIREPLACE:
                            # future functionality
                            pass

                        elif device["type"] == API_DEVICE_MOTORIZED_SHADES:
                            # future functionality
                            pass

                        elif device["type"] == API_DEVICE_GENERIC_DEVICE:
                            # future functionality
                            pass
                
                # Update the node status for the bridge (force reporting)
                bridge.updateNodeStates(True)

        # send custom data added by new nodes to polyglot
        self.saveCustomData(self._customData)

    drivers = [
        {"driver": "ST", "value": 0, "uom": _ISY_BOOL_UOM}
    ]
    commands = {
        "DISCOVER": cmd_discover,
        "UPDATE_PROFILE" : cmd_updateProfile
    }

# Removes invalid charaters and lowercase ISY Node address
def getValidNodeAddress(s):

    # remove <>`~!@#$%^&*(){}[]?/\;:"' characters
    addr = re.sub(r"[<>`~!@#$%^&*(){}[\]?/\\;:\"']+", "", s)

    # return lowercase address
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