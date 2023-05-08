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
    min_temperature = min(all_weather_data, key=lambda x: x[2])[2]
    max_wind_speed = max(all_weather_data, key=lambda x: x[1])[1]
    min_wind_speed = min(all_weather_data, key=lambda x: x[1])[1]
    max_chance_of_rain = max([x[3].get("3h", 0) for x in all_weather_data])
    min_chance_of_rain = min([x[3].get("3h", 0) for x in all_weather_data])

    print(f"Current weather in Billinge, UK:")

    color_wind_speed(wind_speed_mph, min_wind_speed, max_wind_speed)
    color_temperature(temperature_c, max_temperature, min_temperature)
    color_chance_of_rain(
        chance_of_rain.get("3h", 0), min_chance_of_rain, max_chance_of_rain
    )
    print()

    print("Hourly forecast for the rest of the day:\n")

    for local_time, wind_speed_mph, temperature_c, chance_of_rain in hourly_forecast:
        time_str = local_time.strftime("%H:%M:%S")
        print(time_str)

        color_temperature(temperature_c, max_temperature, min_temperature)
        color_wind_speed(wind_speed_mph, min_wind_speed, max_wind_speed)
        color_chance_of_rain(
            chance_of_rain.get("3h", 0), min_chance_of_rain, max_chance_of_rain
        )

        print()


def color_temperature(temp, max_temp, min_temp):
    if temp == max_temp:
        print(f"\033[32mTemperature: {temp:.2f} °C\033[0m")
    elif temp == min_temp:
        print(f"\033[31mTemperature: {temp:.2f} °C\033[0m")
    else:
        print(f"Temperature: {temp:.2f} °C")


def color_wind_speed(wind_speed, min_wind_speed, max_wind_speed):
    if wind_speed == min_wind_speed:
        print(f"\033[32mWind speed: {wind_speed:.2f} mph\033[0m")
    elif wind_speed == max_wind_speed:
        print(f"\033[31mWind speed: {wind_speed:.2f} mph\033[0m")
    else:
        print(f"Wind speed: {wind_speed:.2f} mph")


def color_chance_of_rain(rain_value, min_rain_value, max_rain_value):
    if rain_value == min_rain_value:
        print(f"\033[32mChance of rain: {rain_value}\033[0m")
    elif rain_value == max_rain_value:
        print(f"\033[31mChance of rain: {rain_value}\033[0m")
    else:
        print(f"Chance of rain: {rain_value}")
