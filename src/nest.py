import json
import os
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from logger import logger
from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_PROJECT_ID,
)

TOKEN_FILE = "tokens.json"
AUTH_URL = "https://nestservices.google.com/partnerconnections/{project_id}/auth"
TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
SDM_BASE_URL = "https://smartdevicemanagement.googleapis.com/v1"
REDIRECT_URI = "http://localhost:8080"


class NestClient:
    def __init__(self):
        self.project_id = GOOGLE_PROJECT_ID
        self.client_id = GOOGLE_CLIENT_ID
        self.client_secret = GOOGLE_CLIENT_SECRET
        self.redirect_uri = REDIRECT_URI
        self.access_token = None
        self.refresh_token = None
        self._load_tokens()

    # --- Auth ---

    def _load_tokens(self):
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "r") as f:
                tokens = json.load(f)
                self.access_token = tokens.get("access_token")
                self.refresh_token = tokens.get("refresh_token")
            logger.debug("Tokens loaded from file.")

    def _save_tokens(self, tokens):
        with open(TOKEN_FILE, "w") as f:
            json.dump(tokens, f)
        logger.debug("Tokens saved to file.")

    def get_authorization_url(self):
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/sdm.service",
            "access_type": "offline",
        }
        url = AUTH_URL.format(project_id=self.project_id)
        req = requests.Request("GET", url, params=params).prepare()
        return req.url

    def authorize(self):
        auth_code = self._capture_auth_code()
        response = requests.post(TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
            "code": auth_code,
        })
        response.raise_for_status()
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        self._save_tokens(tokens)
        logger.info("Authorization successful.")

    def _capture_auth_code(self):
        captured = {}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = parse_qs(urlparse(self.path).query)
                captured["code"] = params.get("code", [None])[0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Authorization successful! You can close this tab.")

            def log_message(self, format, *args):
                pass  # suppress server logs

        server = HTTPServer(("localhost", 8080), Handler)
        server.handle_request()
        return captured["code"]

    def refresh_access_token(self):
        response = requests.post(TOKEN_URL, data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        })
        response.raise_for_status()
        tokens = response.json()
        self.access_token = tokens["access_token"]
        tokens["refresh_token"] = self.refresh_token
        self._save_tokens(tokens)
        logger.info("Access token refreshed.")

    def _headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    def _get(self, url):
        response = requests.get(url, headers=self._headers())
        if response.status_code == 401:
            self.refresh_access_token()
            response = requests.get(url, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def _post(self, url, payload):
        response = requests.post(url, headers=self._headers(), json=payload)
        if response.status_code == 401:
            self.refresh_access_token()
            response = requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()
        return response.json()

    # --- Devices ---

    def get_devices(self):
        url = f"{SDM_BASE_URL}/enterprises/{self.project_id}/devices"
        data = self._get(url)
        devices = data.get("devices", [])
        logger.info(f"Found {len(devices)} device(s).")
        return devices

    def get_thermostats(self):
        devices = self.get_devices()
        return [d for d in devices if "sdm.devices.types.THERMOSTAT" in d.get("type", "")]

    # --- Thermostat controls ---

    def get_all_traits(self, device_id):
        url = f"{SDM_BASE_URL}/enterprises/{self.project_id}/devices/{device_id}"
        data = self._get(url)
        return data.get("traits", {})

    def get_status(self, device_id):
        traits = self.get_all_traits(device_id)

        def c_to_f(c):
            return c * 9 / 5 + 32 if c is not None else None

        temp_c = traits.get("sdm.devices.traits.Temperature", {}).get("ambientTemperatureCelsius")
        humidity = traits.get("sdm.devices.traits.Humidity", {}).get("ambientHumidityPercent")
        hvac_status = traits.get("sdm.devices.traits.ThermostatHvac", {}).get("status")
        mode = traits.get("sdm.devices.traits.ThermostatMode", {}).get("mode")
        eco = traits.get("sdm.devices.traits.ThermostatEco", {}).get("mode")
        heat_sp = traits.get("sdm.devices.traits.ThermostatTemperatureSetpoint", {}).get("heatCelsius")
        cool_sp = traits.get("sdm.devices.traits.ThermostatTemperatureSetpoint", {}).get("coolCelsius")
        connectivity = traits.get("sdm.devices.traits.Connectivity", {}).get("status")
        fan = traits.get("sdm.devices.traits.Fan", {}).get("timerMode")
        temp_scale = traits.get("sdm.devices.traits.Settings", {}).get("temperatureScale", "CELSIUS")

        return {
            "connectivity":    connectivity,
            "temperature_c":   temp_c,
            "temperature_f":   c_to_f(temp_c),
            "humidity":        humidity,
            "hvac_status":     hvac_status,
            "mode":            mode,
            "eco_mode":        eco,
            "heat_setpoint_c": heat_sp,
            "heat_setpoint_f": c_to_f(heat_sp),
            "cool_setpoint_c": cool_sp,
            "cool_setpoint_f": c_to_f(cool_sp),
            "fan":             fan,
            "temp_scale":      temp_scale,
        }

    def get_temperature(self, device_id):
        traits = self.get_all_traits(device_id)
        temp = traits.get("sdm.devices.traits.Temperature", {}).get("ambientTemperatureCelsius")
        logger.info(f"Current temperature: {temp}°C")
        return temp

    def get_hvac_mode(self, device_id):
        traits = self.get_all_traits(device_id)
        mode = traits.get("sdm.devices.traits.ThermostatMode", {}).get("mode")
        logger.info(f"HVAC mode: {mode}")
        return mode

    def set_hvac_mode(self, device_id, mode):
        """Mode options: HEAT, COOL, HEATCOOL, OFF"""
        url = f"{SDM_BASE_URL}/enterprises/{self.project_id}/devices/{device_id}:executeCommand"
        payload = {
            "command": "sdm.devices.commands.ThermostatMode.SetMode",
            "params": {"mode": mode},
        }
        result = self._post(url, payload)
        logger.info(f"HVAC mode set to {mode}.")
        return result

    def set_temperature(self, device_id, temperature_celsius, mode="HEAT"):
        """Set target temperature. Mode determines which setpoint to use: HEAT or COOL."""
        url = f"{SDM_BASE_URL}/enterprises/{self.project_id}/devices/{device_id}:executeCommand"
        if mode == "HEAT":
            command = "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat"
            params = {"heatCelsius": temperature_celsius}
        elif mode == "COOL":
            command = "sdm.devices.commands.ThermostatTemperatureSetpoint.SetCool"
            params = {"coolCelsius": temperature_celsius}
        else:
            raise ValueError("mode must be 'HEAT' or 'COOL'")
        payload = {"command": command, "params": params}
        result = self._post(url, payload)
        logger.info(f"Temperature set to {temperature_celsius}°C ({mode}).")
        return result
