# Restore plan

This plan removes only the configuration added by Personal Wi-Fi Extender.
It does not reset Docker, firewalld globally, NetworkManager globally, the internal Wi-Fi connection, or any container.

## Scope

The extender added these local artifacts:

- NetworkManager connection: `extender-usb`
- NetworkManager dnsmasq setting: `/etc/NetworkManager/dnsmasq-shared.d/extender-broadcast.conf`
- firewalld zone: `personal-wifi-extender`
- firewalld policy: `pwe-nat`
- temporary `DOCKER-USER` rules for `10.42.0.0/24`
- runtime watch process and `/run/extender-watch.pid`
- local scripts, UI, desktop launcher and optional Git repository

The original `Eolo_euEmcg` connection on the internal Wi-Fi card must remain untouched.

## Before starting

1. Disconnect all devices from the extended Wi-Fi.
2. Confirm that the internal Wi-Fi still has Internet access:

   ```bash
   ping -c 2 -I wlp0s20f3 1.1.1.1
   ```

3. Open a local terminal in the extender directory:

   ```bash
   cd ~/Desktop/extender
   ```

## 1. Stop the extender

```bash
sudo ./extender_go --stop
```

Expected result: `Casa-Extender` disappears. `Eolo_euEmcg` stays connected.

If the script is unavailable, stop only the NetworkManager profile:

```bash
sudo nmcli connection down extender-usb
```

## 2. Remove forwarding exceptions

The following commands remove only the two rules created for the extender. They do not restart Docker.

```bash
sudo iptables -D DOCKER-USER -s 10.42.0.0/24 -o wlp0s20f3 -j ACCEPT 2>/dev/null || true
sudo iptables -D DOCKER-USER -d 10.42.0.0/24 -i wlp0s20f3 -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true
```

Verify that no extender rule remains:

```bash
sudo iptables -S DOCKER-USER | grep 10.42.0.0/24 || true
```

## 3. Remove the dedicated firewall configuration

```bash
sudo firewall-cmd --permanent --delete-policy=pwe-nat
sudo firewall-cmd --permanent --delete-zone=personal-wifi-extender
sudo firewall-cmd --reload
```

This removes only the extender zone and NAT policy. Do not run `firewall-cmd --complete-reload`, `--panic-on`, or reset firewalld globally.

Verify:

```bash
firewall-cmd --get-zones | tr ' ' '\n' | grep personal-wifi-extender || true
firewall-cmd --get-policies | tr ' ' '\n' | grep pwe-nat || true
```

## 4. Remove the NetworkManager profile and DHCP override

```bash
sudo nmcli connection delete extender-usb
sudo rm -f /etc/NetworkManager/dnsmasq-shared.d/extender-broadcast.conf
```

The dnsmasq file enabled broadcast DHCP replies. Removing it only affects future NetworkManager shared connections.

## 5. Remove runtime and local artifacts

```bash
sudo rm -f /run/extender-watch.pid /var/log/extender-watch.log
rm -f ~/Desktop/personal-wifi-extender.desktop
rm -f ~/.local/share/applications/personal-wifi-extender.desktop
```

Optional: remove the project directory only after saving or pushing any work you want to keep:

```bash
rm -rf ~/Desktop/extender
```

Do not run the optional command unless the project source is no longer needed.

## Final verification

```bash
nmcli -t -f DEVICE,STATE,CONNECTION device
firewall-cmd --get-active-zones
sudo iptables -S DOCKER-USER
ping -c 2 -I wlp0s20f3 1.1.1.1
```

Expected result:

- no `extender-usb` profile or `Casa-Extender` access point;
- no `personal-wifi-extender` zone or `pwe-nat` policy;
- no `10.42.0.0/24` rule in `DOCKER-USER`;
- Docker remains running with its own rules;
- the internal Wi-Fi stays connected to `Eolo_euEmcg`.
