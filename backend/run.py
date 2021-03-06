from flask import Flask, request
from html.parser import HTMLParser
import requests, os, asyncio, time, pytz
from datetime import datetime

from twilio.twiml.messaging_response import MessagingResponse

from twilio.rest import Client
import os

# Your Account Sid and Auth Token from twilio.com/console
account_sid = os.environ['TWILIOASID']
auth_token = os.environ['TWILIOATOKEN']
twilnumber = os.environ['NUMBER']
client = Client(account_sid, auth_token)

app = Flask(__name__)

gKey = os.environ['GMAPTOKEN'] #google api key
#HTML Stripper
class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

#Routes
#DEFAULT TWILIO, 1600 char limit
@app.route("/sms", methods=['GET', 'POST'])
def reply_twilio():
    """Respond to incoming messages with a friendly SMS."""
    # Start our response
    resp = MessagingResponse()
    body = request.args.get('Body').split()

    resp.message(get_reply(body))
    return str(resp)

def getWeather(origin='43.659624,-79.39849007'):
    key = "0864784f871251ec16fe836de0ea3352"
    url = "https://api.darksky.net/forecast/"+key+"/"+origin
    resp = requests.get(url)
    temp = resp.json()
    fehrenheit = temp["currently"]["temperature"]
    celcius = int((fehrenheit - 32) * (5/9))

    msg = "The temperature is " + str(celcius) + " celcius. "
    msg += temp["hourly"]["summary"]
    return msg

@app.route("/stdlib", methods=['POST'])
def sms_stdlib():
    """Respond to incoming messages with a friendly SMS."""
    body = request.json
    incoming = body['msg']
    reply = get_reply(incoming)
    
    message = client.messages \
                    .create(
                         body=reply,
                         from_=twilnumber,
                         to=body['number']
                     )
    return 'done'

def get_reply(body):
    message = ''
    
    longLat = body[-1]
    if 'take' in body:
      #route api to find directions
      dest=body[3:len(body)-2]
      destination="+".join(dest)
      message = getRespfromGoogle(longLat, destination)
    elif 'where' in body:
      #geocoding api
      message = getLocation(longLat)
    elif "weather" in body:
      #weather api
      message = getWeather()
    elif 'time' in body:
      #timezone api
      message = getTimeFromGoogle(longLat)
    elif 'best' in body:
      message = "SMS Assistant is the best app."
    else:
      message = "Sorry, command not supported."

    return message

def getTimeFromGoogle(origin='43.659624,-79.39849007'):
  url = 'https://maps.googleapis.com/maps/api/timezone/json?location='+origin
  #38.908133,-77.047119
  url += '&timestamp=' + str(round(time.time()))
  url += '&key='+gKey
  req = requests.get(url)
  if req.status_code!=200: #if response was unsucessful
    return ["error"]

  timeJson = req.json()

  ret = "You are in " + timeJson['timeZoneName'] + ". It is now "
  tz = datetime.now(pytz.timezone(timeJson['timeZoneId']))
  time_now = tz.time()
  date_now = tz.date()
  ret += str(time_now.hour) + ':' + str(time_now.minute)
  ret += " on "
  ret += str(date_now)

  return ret

def getRespfromGoogle(origin = "bahen+uoft", destination = "hart+house", travelType = "walking"):
    #Using Google maps API to retreive directions from origin to destination
    map = "" #our string to request from Google maps
    map += "https://maps.googleapis.com/maps/api/directions/json?origin="+origin
    map += "&destination=" + destination
    map += "&mode=" + travelType
    map += "&key="+gKey
    req = requests.get(map)

    if req.status_code!=200: #if response was unsucessful
        return ["error"]

    directionsJson = req.json()

    for i in directionsJson['geocoded_waypoints']: #check if valid origin and destination
        if i['geocoder_status']!="OK":
            return ["direction error"]
    # directions now gives us a JSON of directions to reach the dest.
    directions = directionsJson['routes'][0]['legs'][0]
    statement = "\nFrom your location, you are " + directions['distance']['text'] + ", away.\n"
    statement+= "\n It will take "+directions['duration']['text'] + ", to reach " + directions['end_address']+".\n\n"
    step_count = 1
    steps = statement #steps is a list of directions to reach dest.

    for i in directions['steps']:
        step = "Step " + str(step_count) + ": "
        instructions = strip_tags(i['html_instructions'])
        step+= instructions + " "
        step+= "for "+i['distance']['text'] + " which will take " +i['duration']['text'] + "\n";
        step_count+=1
        steps+= step

    return steps

def getLocation (origin = "40.714224,-73.961452"):
    location = "" #our string to request from Google maps
    location += "https://maps.googleapis.com/maps/api/geocode/json?"
    location += "latlng=" + origin
    location += "&key=" + gKey
    req = requests.get(location)

    if req.status_code!=200: #if response was unsucessful
        return ["error"]

    locationJson = req.json()
    general = locationJson['plus_code']
    cityUncleaned = general['compound_code']
    city = cityUncleaned[8:]
    message = "You are currently in " + city
    return message
