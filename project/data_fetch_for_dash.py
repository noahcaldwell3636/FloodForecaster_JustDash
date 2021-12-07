from datetime import timedelta
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import datetime
from dateutil import tz
import pandas as pd
from win32api import GetSystemMetrics
from climacell_api.client import ClimacellApiClient




class FloodData:
    """

    """
    def convert_str_to_datetime(self, dt: str) -> datetime.datetime:
        """ 
        Converts datetime string from the xml doc to a datetime object.
        """
        try:
            time = datetime.datetime.strptime(dt, "%Y-%m-%d %I:%M:%S %p")
        except:
            try:
                time = datetime.datetime.strptime(dt[:-6], "%Y-%m-%dT%H:%M:%S")
            except:
                try:
                    time = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
                except:
                    raise ValueError("~Boone~ this method is meant to convert string into datetime objects, +"
                    "in the following format \n %Y-%m-%d %I:%M:%S %p \n %Y-%m-%dT%H:%M:%S")
        dt = datetime.datetime(year=int(time.year), month=int(time.month), day=int(time.day), hour=int(time.hour), minute=int(time.minute))
        return dt


    def format_datetime(self, dt: datetime.datetime, date: bool = True) -> str:
        if date:
            return dt.strftime('%Y-%m-%d %I:%M %p')
        else:
            return dt.strftime('%I:%M %p')


    def get_xml_root(self, url: str) -> ET.Element:
        data_page = urlopen(url)
        xml_doc = ET.parse(data_page)
        return xml_doc.getroot()



    def bridge_to_fore(self,
        observed_df: pd.DataFrame, 
        filled_forecast_df: pd.DataFrame
        ) -> pd.DataFrame:

        """ Returns a pandas dataframe of fill data accounting for the gap between the 
        end of the observed flood level data and the forecasted flood level data."""

        # start of data bridge = obs_last_time
        obs_last_time = str(observed_df['Time'].iloc[-1])
        obs_last_time = self.convert_str_to_datetime(obs_last_time)
        # end of data bridge = for_fist_time
        fore_first_time = str(filled_forecast_df['Time'].iloc[0]) 
        fore_first_time = self.convert_str_to_datetime(fore_first_time)
        # get the difference in time between the gap
        hours_difference = (fore_first_time - obs_last_time).total_seconds() / 60 / 60
        intervals = int(hours_difference * 4) # number of 15 minute intervals
        
        # create list of all time values in the bridge
        bridge_times = []
        t = obs_last_time + datetime.timedelta(minutes=15)
        bridge_times.append(self.format_datetime(t))
        for i in range(intervals-2): # minues two b/c the first and last points are included on the observed df and the orginal df
            t = t + datetime.timedelta(minutes=15)
            bridge_times.append(t)

        # get beginning and ending forecast levels
        start_level = float(observed_df['Level'].iloc[-1])
        end_level = float(filled_forecast_df['Level'].iloc[0])
        # get list of levels using Euler's Rule
        level_range = float(end_level) - float(start_level)
        increment = level_range / intervals
        bridge_levels = []
        lvl = float(start_level + increment)
        bridge_levels.append(lvl)
        for k in range(intervals-2): # minues two b/c the first and last points are included on the observed df and the orginal df
            lvl += increment
            bridge_levels.append(lvl)
        
        bridge_data = pd.DataFrame(dict(Level=bridge_levels, Time=bridge_times))
        joint_bridge_forecast = pd.concat([bridge_data, filled_forecast_df])

        return joint_bridge_forecast


    def fill_missing_time(self, given_times: list) -> list:
        """ Adds filler points to the forecast plot to account for the data being
        in 6 hour intervals instead of 15 minute intrevals like the observed plot.
        Allows the time and plot size to be consistent amongst the two plots. 

        @param time - list of datetimes
        """
        adjusted_times = []
        for i in range(len(given_times)-1):
            adjusted_times.append(given_times[i])
            fill_time = given_times[i] + datetime.timedelta(minutes=15)
            adjusted_times.append(fill_time)
            while fill_time < given_times[i+1]:
                fill_time = fill_time + datetime.timedelta(minutes=15)
                adjusted_times.append(fill_time)
        return adjusted_times


    def fill_missing_levels(self, levels: list) -> list:
        adjusted_levels = []
        for i in range(len(levels)):
            current_level = float(levels[i])
            adjusted_levels.append(float(current_level))
            try:
                next_level = float(levels[i+1])
            except:
                break
            # compute rate of change per increment
            points = 23 # 24, 15-minute segments in 6 hours. Minus the last point because it it the next point
            rate_of_change = (1/points) * (next_level-current_level)
            # create each fill point
            fill_point = current_level + rate_of_change
            adjusted_levels.append(float(fill_point))
            for j in range(points-1): # create next points except for the last point which is given in the level param
                fill_point = fill_point + rate_of_change
                adjusted_levels.append(float(fill_point))
        return adjusted_levels


    def get_flood_data(self, xml_root: ET.Element, observed_or_forecast: str) -> pd.DataFrame:
        xml_elements = xml_root.findall(observed_or_forecast + '/datum')
        levels = []
        time_list = []
        # get parse xml elements with flood data
        for datum in xml_elements:
            date_UTC_str = datum.find('valid').text
            water_level = datum.find('primary').text # in feet
            levels.append(float(water_level))
            dt = self.convert_str_to_datetime(date_UTC_str)
            time_list.append(dt)
        # format xml data for dash
        if observed_or_forecast == 'observed': #observed data is flipped in xml
            time_list.reverse()
            levels.reverse()
        elif observed_or_forecast == 'forecast': #forecasted data is incremented by 6hours not 15min
            time_list = self.fill_missing_time(time_list)
            levels = self.fill_missing_levels(levels)
        else:
            raise ValueError("~Boone~ the get_flood_data method expects the 'observed' or 'forecast'.")
        data = list(zip(time_list, levels))
        return pd.DataFrame(data, columns=['Time', 'Level'])


    def get_screen_resolution(self) -> dict:
        return {"width": GetSystemMetrics(0), "height": GetSystemMetrics(1)}


    def get_observed_data(self) -> pd.DataFrame:
        # get xml object from the internet
        xml_root = self.get_xml_root(url='https://water.weather.gov/ahps2/hydrograph_to_xml.php?gage=rmdv2&output=xml')
        return self.get_flood_data(xml_root, "observed")


    def get_forecast_data(self) -> pd.DataFrame:
        xml_root = self.get_xml_root(url='https://water.weather.gov/ahps2/hydrograph_to_xml.php?gage=rmdv2&output=xml')
        return self.get_flood_data(xml_root, "forecast")


    def get_mins_from_midnight(self, alt_time: datetime.datetime = None) -> int:
        if alt_time:
            return (alt_time.hour * 60) + alt_time.minute
        else:
            now = datetime.datetime.now()
            return (now.hour * 60) + now.minute


    def get_gradient(self,
                    n: int,
                    sunrise: datetime.datetime,
                    sunset: datetime.datetime,
                    red: str,
                    yellow: str,
                    black: str,
                    ) -> str:
        sunrise = self.get_mins_from_midnight(alt_time=sunrise)
        sunset = self.get_mins_from_midnight(alt_time=sunset)
        end = 24 * 60
        if n == 1:
            sunrise_percent = int((sunrise / end) * 100) + 25
            return f'linear-gradient(90deg, #000000 {sunrise_percent - 15}%, {red} {sunrise_percent}%, rgba(0,212,255,1) {sunrise_percent + 40}%)'
        elif n == 2:
            sunset_percent = int((sunset / end) * 100) - 25
            return f'linear-gradient(90deg, rgba(0,212,255,1) {sunset_percent - 40}%, {red} {sunset_percent}%, #000000  {sunset_percent + 15}%)'


    def convert_utc_est(self, utc: datetime.datetime) -> datetime.datetime:
        from_zone = tz.gettz('UTC')
        to_zone = tz.gettz('America/New_York')
        utc = utc.replace(tzinfo=from_zone)
        return utc.astimezone(to_zone)


    def get_time(self) -> str:
        time = datetime.datetime.now().strftime('%I:%M')
        if time[0] == '0':
            return time[1:]
        return time


    def get_time_postfix(self) -> str:
        return datetime.datetime.now().strftime('%p')


    def get_date(self) -> str:
        return datetime.datetime.now().strftime('%x')


# class ClimaTools:
#     def get_climacell_data(self) -> dict:
#         key = "96Sx5iofKooIKqeBycfPBZfAmOTSnUa1"
#         client = ClimacellApiClient(key)
#         # 4700 welby turn = (37.558331, -77.639555)
#         rt = client.realtime(
#             lat=37.558,
#             lon=-77.639,
#             fields=[
#                 "temp",
#                 "feels_like",
#                 "humidity",
#                 "wind_speed",
#                 "wind_gust",
#                 "baro_pressure",
#                 "precipitation",
#                 "precipitation_type",
#                 "sunrise",
#                 "sunset",
#                 "visibility",
#                 "cloud_cover",
#                 "weather_code",
#             ],
#         )
#         rt_data = rt.data()

#         # Sometimes Clima cell gives data errors this try-except statement
#         # will use the most recent data it did fetch. This will return a dictionary
#         # with dumby data so development can continue
#         try:
#             rt_measurements = rt_data.measurements
#         except AttributeError as e:
#             return {
#                 "obs_time": None,
#                 "lat": None,
#                 "long": None,
#                 "temp_value": None,
#                 "temp_units": None,
#                 "feels_like_value": None,
#                 "feels_like_units": None,
#                 "humidity_value": None,
#                 "humidity_units": None,
#                 "wind_speed_value": None,
#                 "wind_speed_units": None,
#                 "wind_gust_value": None,
#                 "wind_gust_units": None,
#                 "baro_pressure_value": None,
#                 "baro_pressure_units": None,
#                 "precipitation_value": None,
#                 "precipitation_units": None,
#                 "precipitation_type_value": None,
#                 "sunrise_value": None,
#                 "sunset_value": None,
#                 "visibility_value": None,
#                 "visibility_units": None,
#                 "cloud_cover_value": None,
#                 "cloud_cover_units": None,
#                 "weather_code_value": None,
#             }

#         return {
#             "obs_time": convert_utc_est(rt_data.observation_time),
#             "lat": rt_data.lat,
#             "long": rt_data.lon,
#             "temp_value": convert_to_farhrenheit(rt_measurements["temp"].value),
#             "temp_units": "F\N{DEGREE SIGN}",
#             "feels_like_value": convert_to_farhrenheit(
#                 rt_measurements["feels_like"].value
#             ),
#             "feels_like_units": "F\N{DEGREE SIGN}",
#             "humidity_value": rt_measurements["humidity"].value,
#             "humidity_units": rt_measurements["humidity"].units,
#             "wind_speed_value": rt_measurements["wind_speed"].value,
#             "wind_speed_units": rt_measurements["wind_speed"].units,
#             "wind_gust_value": rt_measurements["wind_gust"].value,
#             "wind_gust_units": rt_measurements["wind_gust"].units,
#             "baro_pressure_value": rt_measurements["baro_pressure"].value,
#             "baro_pressure_units": rt_measurements["baro_pressure"].units,
#             "precipitation_value": rt_measurements["precipitation"].value,
#             "precipitation_units": rt_measurements["precipitation"].units,
#             "precipitation_type_value": rt_measurements["precipitation_type"].value,
#             "sunrise_value": convert_utc_est(
#                 convert_str_to_datetime(rt_measurements["sunrise"].value)
#             ),
#             "sunset_value": convert_utc_est(
#                 convert_str_to_datetime(rt_measurements["sunset"].value)
#             ),
#             "visibility_value": rt_measurements["visibility"].value,
#             "visibility_units": rt_measurements["visibility"].units,
#             "cloud_cover_value": rt_measurements["cloud_cover"].value,
#             "cloud_cover_units": rt_measurements["cloud_cover"].units,
#             "weather_code_value": rt_measurements["weather_code"].value,
#         }

#     def convert_to_farhrenheit(self, temp_celcius: float) -> float:
#         temp_celcius /= 5
#         temp_celcius *= 9
#         temp_celcius += 32
#         return temp_celcius
