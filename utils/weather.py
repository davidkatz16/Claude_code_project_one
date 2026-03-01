import requests
from logger import logger

GEOCODE_URL = "https://api.zippopotam.us/us/{zip}"
NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"


class WeatherClient:
    def __init__(self, zip_code):
        self.zip_code = zip_code
        self.lat, self.lon = self._get_coordinates()
        self.observation_url = self._get_observation_url()

    def _get_coordinates(self):
        response = requests.get(GEOCODE_URL.format(zip=self.zip_code))
        response.raise_for_status()
        data = response.json()
        lat = float(data["places"][0]["latitude"])
        lon = float(data["places"][0]["longitude"])
        logger.debug(f"Coordinates for {self.zip_code}: {lat}, {lon}")
        return lat, lon

    def _get_observation_url(self):
        response = requests.get(
            NWS_POINTS_URL.format(lat=round(self.lat, 4), lon=round(self.lon, 4)),
            headers={"User-Agent": "NestThermostatApp/1.0"}
        )
        response.raise_for_status()
        data = response.json()
        stations_url = data["properties"]["observationStations"]

        stations_response = requests.get(
            stations_url,
            headers={"User-Agent": "NestThermostatApp/1.0"}
        )
        stations_response.raise_for_status()
        station_id = stations_response.json()["features"][0]["properties"]["stationIdentifier"]
        logger.debug(f"Using weather station: {station_id}")
        return f"https://api.weather.gov/stations/{station_id}/observations/latest"

    def get_current(self):
        response = requests.get(
            self.observation_url,
            headers={"User-Agent": "NestThermostatApp/1.0"}
        )
        response.raise_for_status()
        props = response.json()["properties"]

        temp_c = props.get("temperature", {}).get("value")
        humidity = props.get("relativeHumidity", {}).get("value")
        description = props.get("textDescription", "N/A")
        wind_speed = props.get("windSpeed", {}).get("value")

        return {
            "description":   description,
            "temperature_c": temp_c,
            "temperature_f": temp_c * 9 / 5 + 32 if temp_c is not None else None,
            "humidity":      round(humidity) if humidity is not None else None,
            "wind_speed_kph": wind_speed,
            "wind_speed_mph": wind_speed * 0.621371 if wind_speed is not None else None,
        }
