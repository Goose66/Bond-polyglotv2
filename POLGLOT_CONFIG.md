## BondBridge NodeServer Configuration
##### Advanced Configuration:
- key: shortPoll, value: polling interval for status from bridge(s) and devices - defaults to 20 seconds (optional)
- key: longPoll - not used

##### Custom Configuration Parameters:
- key: hostname, value: locally accessible hostname or IP address for Bond Bridge (e.g., "192.168.1.145" or "ZZBL45678.local")(optional - if bridge or SBB device not automatically discovered)
- key: token, value: local access token for Bond Bridge. Available in the "Settings" for the bridge in the Bond Home mobile app (optional - if bridge or SBB device not automatically discovered)

Once the "Bonde Nodeserver" node appears in The ISY Administrative Console and shows as Online, press the "Discover Devices" button to load the systems and devices discovered on your local network (LAN).