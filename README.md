# Bond-polyglotv2
A NodeServer for the Polyglot v2 that interfaces to the Olibra Bond Bridge locally to allow the ISY 994i to control the devices (ceiling fans, lights, etc.) supported by the Bridge. May also control Smart by Bond products. See https://bondhome.io/ for more information.

Instructions for local Polyglot-V2 installation:

1. Install the Bond Bridge nodeserver from the Polyglot Nodeserver Store, or do a Git from the repository to the folder ~/.polyglot/nodeservers/Bond in your Polyglot v2 installation.
2. Log into the Polyglot Version 2 Dashboard (https://<Polyglot IP address>:3000)
3. Add the Bond Bridge nodeserver as a Local (Co-Resident with Polyglot) nodeserver type.
4. Add the following required Custom Configuration Parameters under Configuration:
```
    "hostname" = locally accessible hostname or IP address for Bond Bridge (e.g., "192.168.1.145" or "ZZBL45273.local")
    "token" = local access token for Bond Bridge. Available in the "Settings" for the bridge in the Bond Home App.
```
5. Add the following optional Custom Configuration Parameters:
```
    "shortPoll" = polling interval for status from bridge(s) and devices - defaults to 20 (longPoll is not used)
```
6. Once the Bond Bridge NodeServer node appears in ISY994i Adminstative Console, click "Discover Devices" to load nodes for the devices for the specified bridge(s).

Notes:

1. Only Celing Fans and embedded lights are currently supported. The nodeserver creates a separate node for the fan and the embedded light, if there is one. Blinds and fireplaces will be added when devices are available to test.
2. If you have multiple Bond Bridges and/or Smart By Bond devices, specify a hostname and token for each, separated by semicolons (;) in the "hostname" and "token" parmaters. Make sure that the corresponding values are specified in the same order.
3. The ST driver of Ceiling Fan nodes reflects the current speed of the fan as a percentage of the maximum speed, with 0 being 0% (Off) and the maximum speed being 100%. In order to set the fan to a specific, known speed, use the Set Speed command. The Set Speed command lets you set the speed to up to 10 speed numbers. Speed numbers over the maximum speed set the fan to the maximum speed.

For more information regarding this Polyglot Nodeserver, see https://forum.universal-devices.com/topic/?????-polyglot-bond-nodeserver/.