import codes
from weather import Weather, Unit
LOCATION = 1098081
UNITS = Unit.CELSIUS
import datetime

def is_night(weather):
  is_night = True
  current_time = int(weather.timestamp.strftime('%H%M'))
  sunrise = datetime.datetime.strptime(weather.astronomy['sunrise'], '%I:%M %p')
  sunrise = int(sunrise.strftime('%H%M'))
  sunset = datetime.datetime.strptime(weather.astronomy['sunset'], '%I:%M %p')
  sunset = int(sunset.strftime('%H%M'))
  if sunrise <= current_time and current_time < sunset:
    is_night = False
  return is_night

def get_weather():
  weather = Weather(unit=UNITS)
  location = weather.lookup(LOCATION)
  condition = location.condition
  location.timestamp = datetime.datetime.now()
  night = is_night(location)
  code = int(condition.code)
  if (code >= codes.TORNADO and code <= codes.HURRICANE):
    img = 'extreme_wind.png'
  elif (code >= codes.SEVERE_THUNDERSTORMS and code <= codes.THUNDERSTORMS) or (code >= codes.ISOLATED_THUNDERSTORMS and code <= codes.SCATTERED_THUNDERSTORMS) or code == codes.THUNDERSHOWERS or code == codes.ISOLATED_THUNDERSHOWERS:
    if night:
      img = 'night_storm.png'
    else:
      img = 'storm.png'
  elif (code >= codes.FREEZING_DRIZZLE and code <= codes.SHOWERS_2) or condition.code == codes.HAIL or code == codes.MIXED_RAIN_HAIL:
    img = 'rain.png'
  elif (code >= codes.MIXED_RAIN_SNOW and code <= codes.MIXED_SNOW_SLEET) or (code >= codes.SNOW_FLURRIES and code <= codes.SNOW) or (code >= codes.HEAVY_SNOW and code <= codes.HEAVY_SNOW_2) or code == codes.SNOW_SHOWERS or code == codes.SLEET:
    img = 'snow.png'
  elif code == codes.DUST or (code >= codes.SMOKY and code <= codes.WINDY):
    img = 'windy.png'
  elif code == codes.FOGGY or code == codes.HAZE:
    if night:
      img = 'night_fog.png'
    else:
      img = 'fog.png'
  elif (code >= codes.CLEAR_NIGHT and code <= codes.FAIR_DAY) or code == codes.HOT or code == codes.COLD:
    if night:
      location.condition.desc = location.condition.text.replace('sunny', 'clear')
      img = 'night_clear.png'
    else:
      img = 'clear.png'
  elif (code >= codes.CLOUDY and code <= codes.PARTLY_CLOUDY_DAY) or code == codes.PARTLY_CLOUDY:
    img = 'cloudy.png'
  else:
    img = 'not_available.png'
  location.img = img
  location.night = night
  return location
