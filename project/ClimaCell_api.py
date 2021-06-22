from climacell_api.client import ClimacellApiClient
from datetime import datetime as datetime_obj


class ClimaTools:
    def get_climacell_data(self) -> dict:
        key = "96Sx5iofKooIKqeBycfPBZfAmOTSnUa1"
        client = ClimacellApiClient(key)
        # 4700 welby turn = (37.558331, -77.639555)
        rt = client.realtime(
            lat=37.558,
            lon=-77.639,
            fields=[
                "temp",
                "feels_like",
                "humidity",
                "wind_speed",
                "wind_gust",
                "baro_pressure",
                "precipitation",
                "precipitation_type",
                "sunrise",
                "sunset",
                "visibility",
                "cloud_cover",
                "weather_code",
            ],
        )
        rt_data = rt.data()

        # Sometimes Clima cell gives data errors this try-except statement
        # will use the most recent data it did fetch. This will return a dictionary
        # with dumby data so development can continue
        try:
            rt_measurements = rt_data.measurements
        except AttributeError as e:
            return {
                "obs_time": None,
                "lat": None,
                "long": None,
                "temp_value": None,
                "temp_units": None,
                "feels_like_value": None,
                "feels_like_units": None,
                "humidity_value": None,
                "humidity_units": None,
                "wind_speed_value": None,
                "wind_speed_units": None,
                "wind_gust_value": None,
                "wind_gust_units": None,
                "baro_pressure_value": None,
                "baro_pressure_units": None,
                "precipitation_value": None,
                "precipitation_units": None,
                "precipitation_type_value": None,
                "sunrise_value": None,
                "sunset_value": None,
                "visibility_value": None,
                "visibility_units": None,
                "cloud_cover_value": None,
                "cloud_cover_units": None,
                "weather_code_value": None,
            }

        return {
            "obs_time": convert_utc_est(rt_data.observation_time),
            "lat": rt_data.lat,
            "long": rt_data.lon,
            "temp_value": convert_to_farhrenheit(rt_measurements["temp"].value),
            "temp_units": "F\N{DEGREE SIGN}",
            "feels_like_value": convert_to_farhrenheit(
                rt_measurements["feels_like"].value
            ),
            "feels_like_units": "F\N{DEGREE SIGN}",
            "humidity_value": rt_measurements["humidity"].value,
            "humidity_units": rt_measurements["humidity"].units,
            "wind_speed_value": rt_measurements["wind_speed"].value,
            "wind_speed_units": rt_measurements["wind_speed"].units,
            "wind_gust_value": rt_measurements["wind_gust"].value,
            "wind_gust_units": rt_measurements["wind_gust"].units,
            "baro_pressure_value": rt_measurements["baro_pressure"].value,
            "baro_pressure_units": rt_measurements["baro_pressure"].units,
            "precipitation_value": rt_measurements["precipitation"].value,
            "precipitation_units": rt_measurements["precipitation"].units,
            "precipitation_type_value": rt_measurements["precipitation_type"].value,
            "sunrise_value": convert_utc_est(
                convert_str_to_datetime(rt_measurements["sunrise"].value)
            ),
            "sunset_value": convert_utc_est(
                convert_str_to_datetime(rt_measurements["sunset"].value)
            ),
            "visibility_value": rt_measurements["visibility"].value,
            "visibility_units": rt_measurements["visibility"].units,
            "cloud_cover_value": rt_measurements["cloud_cover"].value,
            "cloud_cover_units": rt_measurements["cloud_cover"].units,
            "weather_code_value": rt_measurements["weather_code"].value,
        }

    def convert_to_farhrenheit(self, temp_celcius: float) -> float:
        temp_celcius /= 5
        temp_celcius *= 9
        temp_celcius += 32
        return temp_celcius
