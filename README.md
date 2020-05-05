# Bond-polyglotv2
A NodeServer for Polyglot v2 that interfaces to Olibra Bond Bridges and Smart by Bond (SBB) devices locally to allow the ISY 994i to control the devices (ceiling fans, lights, blinds, fireplaces, etc.). See https://bondhome.io/ for more information on Olibra Bond Bridge.

### Instructions for local Polyglot-V2 installation:

From the Polyglot Dashboard:
1. Install the BondBridge nodeserver from the Polyglot Nodeserver Store.
2. Add the BondBridge nodeserver as a Local (Co-Resident with Polyglot) nodeserver type.
3. Modify the following optional Custom Configuration Parameters:

    ##### Advanced Configuration:
    - key: shortPoll, value: polling interval for status from bridge(s) and devices - defaults to 20 (longPoll is not used)

5. Once the "Bond NodeServer" node appears in ISY994i Adminstative Console, unlock the Bond devices on your network (e.g., power cycle your Bond bridge(s)) and then click "Discover Devices" to load nodes for each of the devices setup in your bridge. Once unlocked by power cycling, you have 10 minutes to intiate the Discover Devices command. THIS PROCESS MAY TAKE SEVERAL SECONDS depending on the number of Bond bridges and devices there are, so please be patient and wait 30 seconds or more before retrying. Also, please check the Polyglot Dashboard for messages regarding Discover Devices failure conditions.

### Notes:

1. Your Bond bridge may not be discoverable by the Discover Devices routine depending on the configuration of your network and Wi-Fi. If your Bond Bridge or SBB device is not discoverable, you may connect to it manually by adding the following Custom Configuration Parameters under Configuration in the Polyglot Dashboard and then re-running the Discover Devices command:

    ##### Custom Configuration Parameters:
    - key: hostname, value: locally accessible hostname or IP address for Bond Bridge (e.g., "192.168.1.145" or "ZZBL45678.local").
    - key: token, value: local access token for Bond Bridge. Available in the "Settings" for the bridge in the Bond Home mobile app.

2. You can also specify multiple Bond Bridges and/or SBB devices for Discovery in Custom Configuration Parmaeters by specifying a hostname and token for each, separated by semicolons (;) in the "hostname" and "token" paramaters. Make sure that the corresponding values are specified in the same order.
3. Only very basic functionality for shades, fireplaces, and generic devices (just Open/Close or On/Off functionality). Additional functionality will be added when users with these devices are available to test new code.
4. The ST driver of Ceiling Fan nodes reflects the current speed of the fan as a percentage of the maximum speed, with 0 being 0% (Off) and the maximum speed being 100%. In order to set the fan to a specific, known speed, use the Set Speed command. The Set Speed command lets you set the speed to up to 10 speed numbers. Speed numbers over the maximum speed set the fan to the maximum speed.
5. If your fan has an uplight and downlight, the nodserver will create two light nodes that you can turn on and off seperately. The result of setting the brightness level of either (if available) is unknown since I did not have such a fan to test with.

For more information regarding this Polyglot Nodeserver, see https://forum.universal-devices.com/topic/28463-polyglot-bond-bridge-nodeserver/.
