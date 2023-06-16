import pyowm
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
    chance_of_rain = weather.rain

    return wind_speed_mph, temperature_c, chance_of_rain


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
        chance_of_rain = weather.rain
        hourly_forecast.append(
            (local_time, wind_speed_mph, temperature_c, chance_of_rain)
        )

    return hourly_forecast


def today():
    current_time = datetime.datetime.now()
    wind_speed_mph, temperature_c, chance_of_rain = get_current_weather()
    hourly_forecast = get_hourly_forecast()

    all_weather_data = [
        (current_time, wind_speed_mph, temperature_c, chance_of_rain)
    ] + hourly_forecast

    max_temp_tuple = max(all_weather_data, key=lambda x: x[2])
    min_temp_tuple = min(all_weather_data, key=lambda x: x[2])

    # Generate a human-readable description
    description = (
        f"Low:  {min_temp_tuple[2]:.1f}°C    ({min_temp_tuple[0]:%H:%M}) "
        f"    Wind: {min_temp_tuple[1]:.1f} mph\n"
    )
    description += (
        f"High: {max_temp_tuple[2]:.1f}°C    ({max_temp_tuple[0]:%H:%M}) "
        f"    Wind: {max_temp_tuple[1]:.1f} mph\n"
    )

    no_rain_periods = [
        (time, rain) for time, wind, temp, rain in hourly_forecast if not rain
    ]
    if no_rain_periods:
        if len(no_rain_periods) == len(hourly_forecast):
            description += "No rain for the time period."
        else:
            description += f"It won't rain between {no_rain_periods[0][0]:%H:%M} and {no_rain_periods[-1][0]:%H:%M}."
    else:
        min_rain_tuple = min(hourly_forecast, key=lambda x: x[3].get("3h", 100))
        description += f"Rain today, best time to run between {min_rain_tuple[0]:%H:%M}, with a precipitation probability of {min_rain_tuple[3].get('3h',0)}%."
    print(f"[medium_orchid3]{description}[/medium_orchid3]")
