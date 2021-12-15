import Adafruit_DHT
import time
import requests
import threading
 
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4
 
URL = "http://ec2-3-142-246-224.us-east-2.compute.amazonaws.com:8080"
 
DELAY_UPDATE_SEC = 10
DELAY_SEND_SEC = 60
MIN_TEMP = 20
MAX_TEMP = 30
 
condition = 0 # 0 - normal, 1 - exceeded min, 2 - exceeded max, 3 - sensor failure
new_condition = False #flag change condition
temperature = 0
 
def getSerial():
  # Extract serial from cpuinfo file
  cpuserial = "0000000000000000"
  try:
    f = open('/proc/cpuinfo','r')
     for line in f:
      if line[0:6]=='Serial':
        cpuserial = line[10:26]
    f.close()
  except:
    cpuserial = "ERROR000000000"
  return cpuserial
 
def updateTemperature(event_for_set):
    global temperature
    global condition
    global new_condition
 
    while True:
        event_for_set.clear()
        count = 20
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
        while temperature is None and count > 0:
            #print(f"Repeated questioning {20-count+1}/20")
            time.sleep(1)
            humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
            count = count - 1
        if temperature is None:
            if condition != 3:
                condition = 3
                new_condition = True
        else:
            print("Current temperature = {0:0.1f}C".format(temperature))
            if temperature <= MIN_TEMP and condition != 1:
                condition = 1
                new_condition = True
            if temperature >= MAX_TEMP and condition != 2:
                condition = 2
                new_condition = True
            if temperature > MIN_TEMP and temperature < MAX_TEMP and condition != 0:
                condition = 0
                new_condition = True
        event_for_set.set()
        time.sleep(DELAY_UPDATE_SEC)
 
def sendMessage(event_for_wait):
    global condition
    global new_condition
    while True :
        condition_to_message = {
            0 : "Температура в норме",
            1 : "Температура превысила минимальное значение",
            2 : "Температура превысила максимальное значение",
            3 : "Ошибка сенсора"
        }
        event_for_wait.wait()
        if new_condition:
            requests.post(f"{URL}/push",json={'id':ID, 'message': condition_to_message[condition]})
            print("Send message: ",condition_to_message[condition])
            new_condition = False
        time.sleep(1)
 
def sendTemperature(event_for_wait):
    global condition
    global new_condition
    while True :
        event_for_wait.wait()
        if condition !=3 :
            requests.post(f"{URL}/reading/{ID}?temperature={temperature}")
            print("Sending temperature = {0:0.1f}C".format(temperature))
            #response = requests.get(f"http://192.168.31.251:8080/reading/{ID}")
            #print(response.text)
        else:
            print("Send temperature ERROR")
        time.sleep(DELAY_SEND_SEC)
 
 
serial = getSerial()
response = requests.post(f"{URL}/sensor/?uuid={serial}")
ID = response.text
print (f"Successful registration (serial = {serial}, id = {ID})")
 
 
response = requests.get(f"{URL}/sensor/{ID}").json()
DELAY_UPDATE_SEC = response["updateDelay"]
DELAY_SEND_SEC = response["sendDelay"]
MIN_TEMP = response["minTemp"]
MAX_TEMP = response["maxTemp"]
 
print (f"Successful set settings (DELAY_UPDATE_SEC = {DELAY_UPDATE_SEC}, DELAY_SEND_SEC = {DELAY_SEND_SEC}, MIN_TEMP = {MIN_TEMP}, MAX_TEMP = {MAX_TEMP})")
 
e = threading.Event()
 
t1 = threading.Thread(target = updateTemperature, args = (e,))
t2 = threading.Thread(target = sendMessage, args = (e,))
t3 = threading.Thread(target = sendTemperature, args = (e,))
 
t1.start()
t2.start()
t3.start()
