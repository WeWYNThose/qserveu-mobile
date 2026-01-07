from kivy.utils import platform
import subprocess
import re

class WiFiDetector:
    def __init__(self):
        self.platform = platform

        if self.platform == 'android':
            self.request_android_permissions()

    # ---------------- ANDROID PERMISSIONS ----------------
    def request_android_permissions(self):
        try:
            from android.permissions import request_permissions, Permission

            request_permissions([
                Permission.ACCESS_FINE_LOCATION,
                Permission.ACCESS_COARSE_LOCATION,
                Permission.ACCESS_WIFI_STATE,
                Permission.ACCESS_NETWORK_STATE
            ])
        except Exception as e:
            print("Android permission error:", e)

    # ---------------- WINDOWS WIFI ----------------
    def get_windows_ssid(self):
        try:
            output = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                stderr=subprocess.DEVNULL,
                shell=True,
                text=True
            )

            match = re.search(r"SSID\s*:\s(.+)", output)
            if match:
                ssid = match.group(1).strip()
                if ssid.lower() != "name":
                    return ssid
        except Exception as e:
            print("Windows WiFi error:", e)

        return None

    # ---------------- ANDROID WIFI ----------------
    def get_android_ssid(self):
        try:
            from jnius import autoclass
            from kivy.android import PythonActivity

            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            wifi_manager = activity.getSystemService(Context.WIFI_SERVICE)

            if not wifi_manager.isWifiEnabled():
                return None

            info = wifi_manager.getConnectionInfo()
            ssid = info.getSSID()

            if ssid and ssid != "<unknown ssid>":
                return ssid.strip('"')

        except Exception as e:
            print("Android WiFi error:", e)

        return None

    # ---------------- MAIN METHOD ----------------
    def get_current_ssid(self):
        if self.platform == 'android':
            return self.get_android_ssid()

        elif self.platform == 'win':
            return self.get_windows_ssid()

        else:
            return None

    def get_connection_status(self, target_ssid):
        current_ssid = self.get_current_ssid()

        print(f"🔎 WiFi Check - Current: {current_ssid} | Target: {target_ssid}")

        if not current_ssid:
            return {'connected': False, 'message': "Not connected to WiFi"}

        if current_ssid.lower() == target_ssid.lower():
            return {'connected': True, 'message': f"Connected to {target_ssid}"}

        return {
            'connected': False,
            'message': f"Wrong WiFi: {current_ssid}"
        }
