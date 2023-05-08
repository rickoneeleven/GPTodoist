import pyowm
import datetime
import os

owm = pyowm.OWM(os.environ["OPEN_WEATHER_MAP_API"])
mgr = owm.weather_manager()


def get_current_weather():
    observation = mgr.weather_at_place("Billinge, UK")
    weather = observation.weather

    wind_speed_mph = weather.wind()["speed"] * 2.237  # Convert meters/sec to mph
    temperature_c = weather.temperature("celsius")["temp"]
    chance_of_rain = weather.rain

    return wind_speed_mph, temperature_c, chance_of_rain


def get_hourly_forecast():
    forecaster = mgr.forecast_at_place("Billinge, UK", "3h")
    forecast = forecaster.forecast

    hourly_forecast = []

    # Get today's date
    today = datetime.date.today()

    for weather in forecast:
        # Convert UTC time to local time
        local_time = weather.reference_time("date").astimezone()
        # Check if the forecast is for today and before 8 PM
        if (
            local_time.date() == today
            and local_time.hour >= 8
            and local_time.hour <= 20
        ):
            wind_speed_mph = weather.wind()["speed"] * 2.237
            temperature_c = weather.temperature("celsius")["temp"]
            chance_of_rain = weather.rain
            hourly_forecast.append(
                (local_time, wind_speed_mph, temperature_c, chance_of_rain)
            )

    return hourly_forecast


def today():
    wind_speed_mph, temperature_c, chance_of_rain = get_current_weather()

    hourly_forecast = get_hourly_forecast()

    all_weather_data = [
        (None, wind_speed_mph, temperature_c, chance_of_rain)
    ] + hourly_forecast

    max_temperature = max(all_weather_data, key=lambda x: x[2])[2]
    min_wind_speed = min(all_weather_data, key=lambda x: x[1])[1]
    min_chance_of_rain = min([x[3].get("3h", 0) for x in all_weather_data])

    print("Current weather in Billinge, UK:")

    if wind_speed_mph == min_wind_speed:
        print(f"\033[32mWind speed: {wind_speed_mph:.2f} mph\033[0m")
    else:
        print(f"Wind speed: {wind_speed_mph:.2f} mph")

    if temperature_c == max_temperature:
        print(f"\033[32mTemperature: {temperature_c:.2f} °C\033[0m")
    else:
        print(f"Temperature: {temperature_c:.2f} °C")

    if chance_of_rain.get("3h", 0) == min_chance_of_rain:
        print(f"\033[32mChance of rain: {chance_of_rain}\033[0m\n")
    else:
        print(f"Chance of rain: {chance_of_rain}\n")

    print("Hourly forecast for the rest of the day:\n")

    for local_time, wind_speed_mph, temperature_c, chance_of_rain in hourly_forecast:
        time_str = local_time.strftime("%H:%M:%S")
        print(time_str)

        if temperature_c == max_temperature:
            print(f"\033[32mTemperature: {temperature_c:.2f} °C\033[0m")
        else:
            print(f"Temperature: {temperature_c:.2f} °C")

        if wind_speed_mph == min_wind_speed:
            print(f"\033[32mWind speed: {wind_speed_mph:.2f} mph\033[0m")
        else:
            print(f"Wind speed: {wind_speed_mph:.2f} mph")

        rain_value = chance_of_rain.get("3h", 0)
        if rain_value == min_chance_of_rain:
            print(f"\033[32mChance of rain: {chance_of_rain}\033[0m")
        else:
            print(f"Chance of rain: {chance_of_rain}")

        print()
