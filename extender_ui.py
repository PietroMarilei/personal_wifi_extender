#!/usr/bin/env python3
"""Window to start, stop, and inspect the USB Wi-Fi extender."""

import os
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Vte", "3.91")
from gi.repository import Adw, Gdk, GLib, Gtk, Vte

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(BASE_DIR, "extender_go")
WORK_DIR = BASE_DIR
WATCH_PID = "/run/extender-watch.pid"


def run_cmd(args):
    result = subprocess.run(args, text=True, capture_output=True, check=False)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def wifi_info(name):
    code, info = run_cmd(["iw", "dev", name, "info"])
    data = {"mode": "wifi", "ssid": "", "channel": ""}
    if code != 0:
        return data
    for line in info.splitlines():
        text = line.strip()
        if text.startswith("type "):
            data["mode"] = text.split(None, 1)[1]
        elif text.startswith("ssid "):
            data["ssid"] = text.split(None, 1)[1]
        elif text.startswith("channel "):
            data["channel"] = text.split()[1]
    return data


def collect_status():
    status = {
        "uplink_name": "Not connected",
        "uplink_detail": "The internal Wi-Fi is not connected.",
        "ap_on": False,
        "ap_title": "Down",
        "ap_detail": "The dongle is not transmitting.",
        "clients": "0",
        "watch": "Off",
        "error": "",
    }
    code, devices = run_cmd(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device"])
    if code != 0:
        status["error"] = devices.strip()
        return status

    for line in devices.splitlines():
        parts = line.split(":")
        if len(parts) < 4 or parts[1] != "wifi":
            continue
        name, _kind, state, connection = parts[0], parts[1], parts[2], parts[3]
        info = wifi_info(name)
        if info["mode"] == "AP":
            status["ap_on"] = True
            status["ap_title"] = info["ssid"] or "Access point"
            status["ap_detail"] = "%s · canale %s" % (name, info["channel"] or "?")
            dump_code, dump = run_cmd(["iw", "dev", name, "station", "dump"])
            if dump_code == 0:
                status["clients"] = str(dump.count("Station "))
        elif state == "connected" and status["uplink_name"] == "Not connected":
            status["uplink_name"] = connection or name
            status["uplink_detail"] = "Connected. The internal card is left as it is."

    try:
        with open(WATCH_PID, encoding="utf-8") as handle:
            pid = handle.read().strip()
        if pid:
            alive, _out = run_cmd(["ps", "-p", pid, "-o", "pid="])
            status["watch"] = "On" if alive == 0 else "Off"
    except OSError:
        status["watch"] = "Off"
    return status


def wrapped_label(text, css_class=None):
    label = Gtk.Label(label=text, xalign=0, yalign=0)
    label.set_wrap(True)
    label.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
    label.set_hexpand(True)
    label.set_natural_wrap_mode(Gtk.NaturalWrapMode.NONE)
    if css_class:
        label.add_css_class(css_class)
    return label


def info_row():
    row = Adw.ActionRow()
    row.set_title_lines(2)
    row.set_subtitle_lines(3)
    return row


class ExtenderWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Personal Wi-Fi Extender")
        self.set_default_size(720, 760)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        self.set_content(toolbar)

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(8)
        page.set_margin_bottom(16)
        page.set_margin_start(16)
        page.set_margin_end(16)
        toolbar.set_content(page)

        intro = wrapped_label("Personal Wi-Fi Extender", "title-1")
        page.append(intro)
        hint = wrapped_label(
            "The PC stays on its own Wi-Fi. This window only controls the USB dongle.",
            "dim-label",
        )
        page.append(hint)

        group = Adw.PreferencesGroup()
        self.uplink_row = info_row()
        self.ap_row = info_row()
        self.clients_row = info_row()
        self.watch_row = info_row()
        group.add(self.uplink_row)
        group.add(self.ap_row)
        group.add(self.clients_row)
        group.add(self.watch_row)
        page.append(group)

        buttons = Gtk.Box(spacing=8)
        buttons.set_halign(Gtk.Align.START)
        self.start_button = Gtk.Button(label="Start")
        self.start_button.add_css_class("suggested-action")
        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.add_css_class("destructive-action")
        refresh = Gtk.Button(label="Refresh")
        self.start_button.connect("clicked", self.on_start)
        self.stop_button.connect("clicked", self.on_stop)
        refresh.connect("clicked", self.on_refresh)
        buttons.append(self.start_button)
        buttons.append(self.stop_button)
        buttons.append(refresh)
        page.append(buttons)

        self.note = wrapped_label("Start and Stop type the command into the terminal below.")
        page.append(self.note)

        page.append(wrapped_label("Terminal", "heading"))
        self.terminal = Vte.Terminal()
        self.terminal.set_hexpand(True)
        self.terminal.set_vexpand(True)
        self.terminal.set_size(80, 14)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(220)
        scroll.set_vexpand(True)
        scroll.add_css_class("terminal-frame")
        scroll.set_overflow(Gtk.Overflow.HIDDEN)
        scroll.set_child(self.terminal)
        page.append(scroll)
        self.terminal.spawn_async(
            Vte.PtyFlags.DEFAULT,
            WORK_DIR,
            [os.environ.get("SHELL", "/bin/bash")],
            None,
            GLib.SpawnFlags.DEFAULT,
            None,
            None,
            -1,
            None,
            None,
        )

        self.on_refresh(None)
        GLib.timeout_add_seconds(5, self.on_refresh)

    def paint(self, status):
        self.uplink_row.set_title(status["uplink_name"])
        self.uplink_row.set_subtitle("Uplink. " + status["uplink_detail"])
        self.ap_row.set_title(status["ap_title"])
        self.ap_row.set_subtitle("Access point. " + status["ap_detail"])
        self.clients_row.set_title(status["clients"])
        self.clients_row.set_subtitle("Connected devices.")
        self.watch_row.set_title(status["watch"])
        self.watch_row.set_subtitle("Beacon watch. Restarts the dongle if it stops transmitting.")
        self.ap_row.remove_css_class("ok")
        self.ap_row.remove_css_class("off")
        self.ap_row.add_css_class("ok" if status["ap_on"] else "off")
        if status["error"]:
            self.note.set_text(status["error"])

    def on_refresh(self, _widget=None):
        self.paint(collect_status())
        return True

    def run_script(self, action):
        command = "pkexec %s %s\n" % (SCRIPT, action)
        self.terminal.feed_child(command.encode())
        self.terminal.grab_focus()
        self.note.set_text("Sent: %s" % command.strip())

    def on_start(self, _widget):
        self.run_script("--start")

    def on_stop(self, _widget):
        self.run_script("--stop")


class ExtenderApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="local.personal.wifi.extender")

    def do_startup(self):
        Adw.Application.do_startup(self)
        css = Gtk.CssProvider()
        css.load_from_string(
            ".ok { background: alpha(#2ec27e, 0.18); }"
            ".off { background: alpha(#e5a50a, 0.20); }"
            ".terminal-frame { border-radius: 12px; }"
            ".terminal-frame viewport, .terminal-frame vte-terminal { border-radius: 12px; }"
            ".terminal-frame vte-terminal { padding: 6px 10px; }"
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self):
        window = ExtenderWindow(self)
        window.present()


if __name__ == "__main__":
    raise SystemExit(ExtenderApp().run(None))
