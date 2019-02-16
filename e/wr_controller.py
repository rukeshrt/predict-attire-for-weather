# -*- coding: utf-8 -*-
__author__ = 'Mystique'
"""
.. module: Export Logs from cloudwatch & Store in given S3 Bucket
    :platform: AWS
    :copyright: (c) 2019 Mystique.,
.. moduleauthor:: Mystique
.. contactauthor:: miztiik@github issues
"""

from wr_model import weather_report
from geopy.geocoders import Nominatim
from datetime import datetime,timedelta
import requests, os

DARK_SKY_API_KEY = os.environ.get('DARK_SKY_KEY')
if not DARK_SKY_API_KEY:
    DARK_SKY_API_KEY = "0bdf7cf9b808dec29c52913e70c13f69"

class weather_report_controller: 

    def __init__(self):
        self.option_list = "exclude=currently,minutely,hourly,alerts&units=si"
        """
        if not self.DARK_SKY_API_KEY:
            self.DARK_SKY_API_KEY = "0bdf7cf9b808dec29c52913e70c13f69"
        """
    
    def get_location(self, input_location):
        """
        Get the lattitude and longitude for the given location

        :param input_location: The name of the location
        :param type: str

        :param location: Class Object, Ex: Location(Utrecht, Netherlands, (52.08095165, 5.12768031549829, 0.0))
        :param type: An object of <class 'geopy.location.Location'>
        """
        location = Nominatim().geocode(input_location, language='en_US')
        return location
   
    def predict_attire(self, w_r_data, sensitivity_factors):

        # Set some defaults. All numbers in degree celsius
        # TODO: Push them outside for user customizations
        if not sensitivity_factors:
            sensitivity_factors = {'hot':1, 'cold':1}

        WARM = 24 * sensitivity_factors.get('hot')
        COLD = 10 * sensitivity_factors.get('cold')
        HOT = int( WARM + 0.3*(WARM - COLD) )
        COOL = int( (WARM + COLD) / 2 )
        FREEZING = int(COLD - 1*(COOL - COLD))

        attire = {'clothing':'', 'activity':'', 'top_hat':False, 'boots':False, 'coat':False, 'gloves':False, 'scarves':False, 'sunglasses':False, 'umbrella':False, 'stay_indoor':False }

        if w_r_data.get('raining_chance'):
            attire['umbrella'] = True
            attire['umbrella_emoji'] = f"\U00002614"

        if w_r_data.get('temp_min') >= HOT:
            attire['clothing'] = f"Minimal Outdoor exposure. Stay \U0001F3D8, Stay warm \U0001F379"
            attire['stay_indoor'] = True
        if w_r_data.get('temp_max') >= HOT:
            attire['clothing'] = f"\U0001F3BD Shorts \U0001F576 \U0001F3A9 and \U0001F45F"
            attire['top_hat'] = True
            attire['sunglasses'] = True
        elif w_r_data.get('temp_max') <= HOT and w_r_data.get('temp_max') >= WARM:
            attire['clothing'] = f"\N{t-shirt} Shorts \U0001F576 and \U0001F45F"
            attire['sunglasses'] = True
        elif w_r_data.get('temp_max') <= WARM and w_r_data.get('temp_max') >= COOL:
            attire['clothing'] = f"\N{t-shirt} \N{jeans} Light Jacket and \U0001F9E3"
            attire['scarves'] = True
        elif w_r_data.get('temp_max') <= COOL and w_r_data.get('temp_max') >= COLD:
            attire['clothing'] = f"\N{t-shirt} \N{jeans} Light Jacket \U0001F9E4 \U0001F9E3"
            attire['coat'] = True
            attire['gloves'] = True
            attire['scarves'] = True
        elif w_r_data.get('temp_max') <= COLD and w_r_data.get('temp_max') >= FREEZING:
            attire['clothing'] = f"\N{t-shirt} \N{jeans} Winter Jacket \U0001F9E4 \U0001F9E3 and \U0001F462"
            attire['coat'] = True
            attire['gloves'] = True
            attire['scarves'] = True
            attire['boots'] = True
        elif w_r_data.get('temp_max') <= FREEZING:
            attire['clothing'] = f"Minimal Outdoor exposure. Stay \U0001F3D8, Stay warm \U0001F525 \U00002615"
            attire['stay_indoor'] = True

        return attire

    def get_weather_reports(self, req_data, location):
        """
        Get the weather report for the given location and date
    
        :param data: The JSON data from the form. Ex: {'location': 'Utrecht', 'date_from': '2019-02-14', 'date_to': '2019-02-14'}
        :param type: dict
        :param location: Class Object, Ex: Location(Utrecht, Netherlands, (52.08095165, 5.12768031549829, 0.0))
        :param type: An object of <class 'geopy.location.Location'>
        """
        date_from = req_data.get('date_from')
        date_to = req_data.get('date_to')

        d_from_date = datetime.strptime(date_from , '%Y-%m-%d')
        d_to_date = datetime.strptime(date_to , '%Y-%m-%d')
        delta = d_to_date - d_from_date

        latitude = str(location.latitude)
        longitude = str(location.longitude)

        w_reports = []
        for i in range(delta.days+1):
            w_r_data = { 'temp_min':0,'temp_max':0, 'is_sunny':False, 'will_rain':False }
            new_date = (d_from_date + timedelta(days=i)).strftime('%Y-%m-%d')
            search_date = new_date+"T00:00:00"

            dark_sky_url = (f"https://api.darksky.net/forecast/"
                            f"{DARK_SKY_API_KEY}/"
                            f"{latitude},"
                            f"{longitude},"
                            f"{search_date}?"
                            f"{self.option_list}"
                            )
            print(dark_sky_url)
            try:
                response = requests.get( dark_sky_url )
            except Exception as e:
                return
            wr_data = response.json()
            report_date = (d_from_date + timedelta(days=i)).strftime('%Y-%m-%d %A')

            # Check if it is for US/Rest of the sensible world and tack on appropriate units
            if wr_data['flags']['units'] == 'us':
                unit_type = '°F'
            else:
                unit_type = '°C'

            w_r_data['temp_min'] = wr_data['daily']['data'][0].get('apparentTemperatureMin')
            w_r_data['temp_max'] = wr_data['daily']['data'][0].get('apparentTemperatureMax')
            summary = wr_data['daily']['data'][0].get('summary')

            sunrise = None
            sunset = None
            if wr_data['daily']['data'][0].get('sunriseTime'):
                sunrise = str( datetime.fromtimestamp( wr_data['daily']['data'][0].get('sunriseTime') ).strftime('%H:%M') )
            if wr_data['daily']['data'][0].get('sunsetTime'):
                sunset = str( datetime.fromtimestamp( wr_data['daily']['data'][0].get('sunsetTime') ).strftime('%H:%M') )
            humidity = wr_data['daily']['data'][0].get('humidity')
            humidity *= 100
            humidity = "%.0f%%" % (humidity)

            precip_type = None
            precip_prob = None
            w_r_data['raining_chance'] = None
            if 'precipProbability' in wr_data['daily']['data'][0] and 'precipType' in wr_data['daily']['data'][0]:
                precip_type = wr_data['daily']['data'][0].get('precipType')
                precip_prob = wr_data['daily']['data'][0].get('precipProbability')
            if (precip_type == 'rain' and precip_prob != None):
                precip_prob *= 100
                w_r_data['raining_chance'] = "%.2f%%" % (precip_prob)

            wind_speed = None
            wind_bearing = None
            if 'windSpeed' in wr_data['daily']['data'][0] and wr_data['daily']['data'][0].get('windSpeed') > 0:
                wind_speed = f"{wr_data['daily']['data'][0].get('windSpeed')} Kph"
                wind_bearing = wr_data['daily']['data'][0].get('windBearing')

            icon = wr_data['daily']['data'][0].get('icon')
            if wr_data['daily']['data'][0].get('icon') == "clear-day":
                w_r_data['is_sunny'] = True

            # Lets get the attire predcition
            predicted_attire = self.predict_attire(w_r_data, None)

            # Create a model from the weather report
            # (date, temp_max, temp_min, summary, raining_chance, sunrise, sunset, wind_speed, wind_bearing, humidity, icon)
            w_report = weather_report( report_date,
                                    str(w_r_data['temp_max']) + unit_type,
                                    str(w_r_data['temp_min']) + unit_type,
                                    summary,
                                    w_r_data['raining_chance'],
                                    sunrise,
                                    sunset,
                                    wind_speed,
                                    wind_bearing,
                                    humidity,
                                    icon,
                                    predicted_attire
                                )        
            # Add the report for current date into the list of reports.
            w_reports.append(w_report)

        return w_reports
