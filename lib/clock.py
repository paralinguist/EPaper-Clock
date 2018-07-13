#!/usr/bin/python
import imp
import Image
import ImageDraw
import ImageFont
import ImageOps
import datetime
import sqlite3
from time import sleep
import epd7in5
import weather_display

LIB_DIR      = '/usr/local/lib/epaper_clock/'
FONT_DIR     = '/usr/local/share/fonts/'
TIME_FONT    = FONT_DIR + 'bitsumishi.ttf'
WEATHER_FONT = FONT_DIR + 'danielbd.ttf'
TT_FONT      = FONT_DIR + '04B03.TTF'
TIME_SIZE    = 160
DATE_SIZE    = 80
WEATHER_SIZE = 40

EPD_WIDTH    = 640
EPD_HEIGHT   = 384
EPD_REFRESH  = 6
LEFT_MARGIN  = 40
TOP_MARGIN   = 0
IMAGE_SIZE   = 256
TT_HEIGHT    = 88

WEATHER_CHECK_INTERVAL = 10

#Technique blatantly stolen from SO thread
def get_line_height(text, font):
  ascent, descent = font.getmetrics()
  (width, baseline), (offset_x, offset_y) = font.font.getsize(text)
  line_height = ascent - offset_y + descent
  return line_height, descent

def max_font_size(font, text, width, height):
  size = 1
  max_size = size
  current_tf = ImageFont.truetype(font, size)
  start_width, min_height = current_tf.getsize(text)
  while start_width <= width:
    max_size = max_size * 2
    current_tf = ImageFont.truetype(font, max_size)
    start_width = current_tf.getsize(text)[0]
  current_width, current_height = current_tf.getsize(text)
  while (current_width > width and width > 0) or (current_height > height and height > 0):
    max_size = max_size - 1
    current_tf = ImageFont.truetype(font, max_size)
    current_width, current_height = current_tf.getsize(text)
    size = max_size
  return size

#Assumes a bitmap font optimised for 8/16 pixels
#Splits text into a maximum of 2 lines based on a minimum size of 8
def write_session_text(text_y, text, cell_width, canvas):
  font_size = max_font_size(TT_FONT, text, cell_width-1, 0)
  if font_size < 8:
    text = text.split(' ')
    font_size = min(max_font_size(TT_FONT, text[0], cell_width-1, 0), max_font_size(TT_FONT, text[1], cell_width-1, 0))
    if font_size < 16:
      font_size = 8
    if font_size > 16:
      font_size = 16
    session_font = ImageFont.truetype(TT_FONT, font_size)
    text_x = (cell_width - session_font.getsize(text[0])[0]) // 2
    canvas.text((text_x, text_y), text[0], font = session_font, fill = 0)
    text_y = text_y + session_font.getsize(text[0])[1]
    text = text[1]
  if font_size < 16:
    font_size = 8
  if font_size > 16:
    font_size = 16
  session_font = ImageFont.truetype(TT_FONT, font_size)
  text_x = (cell_width - session_font.getsize(text)[0]) // 2
  canvas.text((text_x, text_y), text, font = session_font, fill = 0)
  text_y = text_y + session_font.getsize(text)[1]
  return text_y

def get_sessions():
  tt_img = Image.new('1', (EPD_WIDTH, 88), 1)
  tt_connection = sqlite3.connect(LIB_DIR + 'timetable.sqlite')
  tt_connection.row_factory = sqlite3.Row
  tt_cursor = tt_connection.cursor()
  current_time = datetime.datetime.now()
  hour = int(current_time.strftime('%H%M'))
  day = current_time.strftime('%A')
  session_sql = """SELECT s.session_number, s.title, s.start_time, s.end_time,
                          e.year_group, e.event_details, e.location
                   FROM sessions s, timetable_days d
                   LEFT JOIN events e on e.session_number = s.session_number 
                     AND e.day = ?
                   WHERE s.timetable_code = d.tt_code AND d.day = ?"""
  shrt = 50
  lng = 78
  next_session_x = 0
  for row in tt_cursor.execute(session_sql, (day, day)):
    start_time = datetime.datetime.strptime(row['start_time'], '%H%M')
    end_time = datetime.datetime.strptime(row['end_time'], '%H%M')
    title = row['title']
    year = row['year_group']
    event = row['event_details']
    location = row['location']
    duration = end_time - start_time
    long_session = duration.total_seconds() > 50*60
    if long_session:
      cell_width = lng
    else:
      cell_width = shrt
    session_img = Image.new('1', (cell_width, 88), 1)
    session_canvas = ImageDraw.Draw(session_img)
    text_y = 0
    session_canvas.line((0, 0, 0, 88))
    text_y = write_session_text(text_y, title, cell_width-2, session_canvas)
    if year:
      text_y = write_session_text(text_y, year, cell_width, session_canvas)
    if event:
      text_y = write_session_text(text_y, event, cell_width, session_canvas)
    if location: 
      text_y = write_session_text(text_y, location, cell_width, session_canvas)
    if int(row['start_time']) <= hour and hour <= int(row['end_time']):
      session_img = session_img.convert('L')
      session_img = ImageOps.invert(session_img)
    tt_img.paste(session_img, (next_session_x,0))
    next_session_x = next_session_x + cell_width
  return tt_img

def get_clock_data():
  current_time = datetime.datetime.now()
  if current_time.second >= 60-EPD_REFRESH:
    current_time = current_time + datetime.timedelta(0,0,0,0,1)
  time = current_time.strftime('%H%M')
  day = current_time.strftime('%A')
  date = current_time.strftime('%-d %B')
  return time, day, date 

epd = epd7in5.EPD()
epd.init()
def push_face(weather):
  image = Image.new('1', (EPD_WIDTH, EPD_HEIGHT), 1)
  draw = ImageDraw.Draw(image)
  tt_img = get_sessions()
  image.paste(tt_img, (0,384-88))
  time_y = TOP_MARGIN
  time_x = LEFT_MARGIN
  #draw.rectangle(((LEFT_MARGIN, TOP_MARGIN), (640-256, 296)))
  #draw.rectangle(((640-256, TOP_MARGIN), (640, 256)))
  #draw.rectangle(((640-256, 256), (640, 296)))
  draw.rectangle(((1, 296), (639, 383)))

  time, day, date = get_clock_data()

  time_width = EPD_WIDTH - LEFT_MARGIN - IMAGE_SIZE
  time_sp_y = (EPD_HEIGHT - TT_HEIGHT) // 2
  day_sp_y = time_sp_y // 2
  date_sp_y = day_sp_y
  time_font_size = max_font_size(TIME_FONT, time, time_width, time_sp_y)
  day_font_size = max_font_size(TIME_FONT, day, time_width, day_sp_y)
  date_font_size = max_font_size(TIME_FONT, date, time_width, date_sp_y)

  time_tf = ImageFont.truetype(TIME_FONT, time_font_size)
  day_tf = ImageFont.truetype(TIME_FONT, day_font_size)
  date_tf = ImageFont.truetype(TIME_FONT, date_font_size)

  time_height, time_offset = get_line_height(time, time_tf)
  time_height = time_tf.getsize(time)[1]
  day_height, date_offset = get_line_height(day, day_tf)
  day_height = day_tf.getsize(day)[1]
  day_y = time_y + time_height
  date_y = day_y + day_height
  draw.text((time_x, time_y), time, font = time_tf, fill = 0)
  draw.text((time_x, day_y), day, font = day_tf, fill = 0)
  draw.text((time_x, date_y), date, font = date_tf, fill = 0)

  weather_img = Image.open(LIB_DIR + weather.img, 'r')
  image.paste(weather_img, (EPD_WIDTH-IMAGE_SIZE,TOP_MARGIN), mask=weather_img)
  weather_text = weather.condition.text + ', ' + weather.condition.temp
  weather_font_size = max_font_size(WEATHER_FONT, weather_text + 'o', IMAGE_SIZE, 0)
  weather_tf = ImageFont.truetype(WEATHER_FONT, weather_font_size)
  weather_text_width, weather_text_height = weather_tf.getsize(weather_text)
  weather_text_x = EPD_WIDTH - IMAGE_SIZE + (IMAGE_SIZE - weather_text_width) // 2
  weather_text_position = (weather_text_x, IMAGE_SIZE)
  draw.text(weather_text_position, weather_text, font = weather_tf, fill = 0)
  degree_top = (weather_text_position[0] + weather_text_width, weather_text_position[1])
  degree_bottom = (degree_top[0] + 7, degree_top[1] + 7)
  degree_box = (degree_top, degree_bottom)
  draw.ellipse(degree_box, fill=None, outline='black')
  if weather.night:
    image = image.convert('L')
    image = ImageOps.invert(image)
  epd.display_frame(epd.get_frame_buffer(image))

weather = weather_display.get_weather()
push_face(weather)
while True:
  sleep(3)
  secs = datetime.datetime.now().second
  if weather.timestamp + datetime.timedelta(0,0,0,0,WEATHER_CHECK_INTERVAL) < datetime.datetime.now():
    check_weather = False
    weather = weather_display.get_weather()
  elif secs >= 60 - EPD_REFRESH:
    push_face(weather)
    check_weather = True
