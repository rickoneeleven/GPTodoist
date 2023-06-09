import pyowm, pytz
import datetime
import os
from rich import print

owm = pyowm.OWM(os.environ["OPEN_WEATHER_MAP_API"])
mgr = owm.weather_manager()


def get_current_weather():
    observation = mgr.weather_at_place("Billinge, UK")
    weather = observation.weather

    wind_speed_mph = weather.wind()["speed"] * 2.237  # Convert meters/sec to mph
    temperature_c = weather.temperature("celsius")["temp"]
    weather_description = weather.detailed_status

    return wind_speed_mph, temperature_c, weather_description


def pretty_print_weather_data():
    wind_speed_mph, temperature_c, weather_description = get_current_weather()

    print("Weather Data:")
    print(f"Location: Billinge, UK")
    print(f"Weather: {weather_description}")
    print(f"Temperature: {temperature_c:.2f}°C")
    print(f"Wind Speed: {wind_speed_mph:.2f} mph")


def get_hourly_forecast():
    forecaster = mgr.forecast_at_place("Billinge, UK", "3h")
    forecast = forecaster.forecast

    hourly_forecast = []
    num_forecasts = 4  # Set the desired number of forecasts

    for weather in forecast:
        # Convert UTC time to local time
        local_time = weather.reference_time("date").astimezone()

        # Check if we already have the desired number of forecasts
        if len(hourly_forecast) >= num_forecasts:
            break

        wind_speed_mph = weather.wind()["speed"] * 2.237
        temperature_c = weather.temperature("celsius")["temp"]
        weather_description = weather.detailed_status
        hourly_forecast.append(
            (local_time, wind_speed_mph, temperature_c, weather_description)
        )

    return hourly_forecast


def today():
    london_tz = pytz.timezone("Europe/London")
    current_time = datetime.datetime.now(london_tz)
    wind_speed_mph, temperature_c, weather_description = get_current_weather()
    hourly_forecast = get_hourly_forecast()

    all_weather_data = [
        (current_time, wind_speed_mph, temperature_c, weather_description)
    ] + hourly_forecast

    max_temp_tuple = max(all_weather_data, key=lambda x: x[2])
    min_temp_tuple = min(all_weather_data, key=lambda x: x[2])

    now_description = (
        f"Now:  {temperature_c:.1f}°C    ({current_time:%H:%M}) "
        f"    Wind: {wind_speed_mph:.1f} mph\n"
    )

    description = (
        f"Low:  {min_temp_tuple[2]:.1f}°C    ({min_temp_tuple[0]:%H:%M}) "
        f"    Wind: {min_temp_tuple[1]:.1f} mph\n"
    )
    description += (
        f"High: {max_temp_tuple[2]:.1f}°C    ({max_temp_tuple[0]:%H:%M}) "
        f"    Wind: {max_temp_tuple[1]:.1f} mph\n"
    )

    # Print rain descriptions with timestamps
    previous_description = weather_description
    description += f"{current_time:%H:%M}: {weather_description}\n"

    for forecast_time, wind_speed, temp, w_description in hourly_forecast:
        if w_description != previous_description:
            description += f"{forecast_time:%H:%M}: {w_description}\n"
            previous_description = w_description

    print(f"{now_description}{description}")


def today_old():
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
        print(f"[red]Temperature: {temp:.2f} °C[/red]")
    elif temp == min_temp:
        print(f"[blue]Temperature: {temp:.2f} °C[/blue]")
    else:
        print(f"Temperature: {temp:.2f} °C")


def color_wind_speed(wind_speed, min_wind_speed, max_wind_speed):
    if wind_speed == min_wind_speed:
        print(f"[green]Wind speed: {wind_speed:.2f} mph[/green]")
    elif wind_speed == max_wind_speed:
        print(f"[red]Wind speed: {wind_speed:.2f} mph[/red]")
    else:
        print(f"Wind speed: {wind_speed:.2f} mph")


def color_chance_of_rain(rain_value, min_rain_value, max_rain_value):
    if rain_value == min_rain_value:
        print(f"[grey]Chance of rain: {rain_value}[/grey]")
    elif rain_value == max_rain_value:
        print(f"[blue]Chance of rain: {rain_value}[/blue]")
    else:
        print(f"Chance of rain: {rain_value}")
