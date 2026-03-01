from src.nest import NestClient


def fahrenheit_to_celsius(f):
    return (f - 32) * 5 / 9


def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32


def show_status(client, device_id):
    temp_c = client.get_temperature(device_id)
    mode = client.get_hvac_mode(device_id)
    print(f"\n  Current temperature : {temp_c:.1f}°C ({celsius_to_fahrenheit(temp_c):.1f}°F)")
    print(f"  HVAC mode           : {mode}")


def change_temperature(client, device_id):
    mode = client.get_hvac_mode(device_id)
    if mode not in ("HEAT", "COOL"):
        print(f"\n  HVAC mode is currently '{mode}'. Set mode to HEAT or COOL first.")
        return

    unit = input("\n  Enter temperature unit (F/C) [F]: ").strip().upper() or "F"
    raw = input(f"  Enter target temperature in °{unit}: ").strip()

    try:
        value = float(raw)
    except ValueError:
        print("  Invalid temperature.")
        return

    temp_c = fahrenheit_to_celsius(value) if unit == "F" else value
    client.set_temperature(device_id, temp_c, mode=mode)
    print(f"  Temperature set to {value}°{unit}.")


def change_mode(client, device_id):
    print("\n  Available modes: HEAT, COOL, HEATCOOL, OFF")
    mode = input("  Enter mode: ").strip().upper()
    if mode not in ("HEAT", "COOL", "HEATCOOL", "OFF"):
        print("  Invalid mode.")
        return
    client.set_hvac_mode(device_id, mode)
    print(f"  Mode set to {mode}.")


def main():
    client = NestClient()

    if not client.access_token:
        url = client.get_authorization_url()
        print(f"\nOpen this URL in your browser to authorize:\n\n{url}\n")
        print("Waiting for authorization...")
        client.authorize()

    thermostats = client.get_thermostats()
    if not thermostats:
        print("No thermostats found.")
        return

    thermostat = thermostats[0]
    device_id = thermostat["name"].split("/")[-1]
    display_name = thermostat.get("traits", {}).get(
        "sdm.devices.traits.Info", {}
    ).get("customName", device_id)

    print(f"\nConnected to: {display_name}")

    while True:
        show_status(client, device_id)
        print("\n  1. Change temperature")
        print("  2. Change HVAC mode")
        print("  3. Refresh status")
        print("  4. Quit")
        choice = input("\n  Select an option: ").strip()

        if choice == "1":
            change_temperature(client, device_id)
        elif choice == "2":
            change_mode(client, device_id)
        elif choice == "3":
            continue
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("  Invalid option.")


if __name__ == "__main__":
    main()
