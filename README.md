# Personal Wi-Fi Extender

The PC stays on its current Wi-Fi. A USB dongle (TP-Link, driver `rtw88_8822bu`) becomes an open access point and shares that connection.

The script finds the dongle by driver, not by USB port name. The internal Wi-Fi card is not reconfigured.

## Setup

```bash
cp extender.env.example extender.env
```

Edit `SSID`, `BAND` and `CHANNEL` in `extender.env`. `extender.env` is local and is not committed.

`BAND=a` and `CHANNEL=36` is 5 GHz. For a 2.4 GHz-only device use `BAND=bg` and `CHANNEL=6`.

## Start and stop

```bash
./extender_go --start
./extender_go --stop
```

`--start` asks for a password through polkit. It brings up the access point, NAT towards the uplink, and a watch that reloads only the dongle driver if the firmware stops sending beacons.

`--stop` turns the access point off and stops the watch. It does not start again at boot.

## Window

```bash
python3 extender_ui.py
```

The window shows uplink, access point, connected devices and the beacon watch. **Start** and **Stop** type the same commands into the embedded terminal. You can also type there yourself.

## Requirements

Fedora with NetworkManager, firewalld, `iptables` and, for the window, GTK 4, libadwaita and VTE. Docker may be running: its `FORWARD` policy drops traffic that is not for a container, so the script adds an exception in `DOCKER-USER` for the extender subnet `10.42.0.0/24` only.
