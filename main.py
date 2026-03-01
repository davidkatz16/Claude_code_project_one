from src.nest import NestClient


def main():
    client = NestClient()

    # First-time authorization
    if not client.access_token:
        url = client.get_authorization_url()
        print(f"\nOpen this URL in your browser to authorize:\n\n{url}\n")
        code = input("Enter the authorization code: ").strip()
        client.authorize(code)

    # List thermostats
    thermostats = client.get_thermostats()
    if not thermostats:
        print("No thermostats found.")
        return

    for thermostat in thermostats:
        device_id = thermostat["name"].split("/")[-1]
        display_name = thermostat.get("traits", {}).get(
            "sdm.devices.traits.Info", {}
        ).get("customName", device_id)

        print(f"\nThermostat: {display_name}")
        temp = client.get_temperature(device_id)
        mode = client.get_hvac_mode(device_id)
        print(f"  Current temperature : {temp}°C ({temp * 9/5 + 32:.1f}°F)")
        print(f"  HVAC mode           : {mode}")


if __name__ == "__main__":
    main()
