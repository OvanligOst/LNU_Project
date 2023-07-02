#Password libs
import credentials as cred    # Contains passwords
#Hardware libs
from dht import DHT11         # Temp and humidity sensor functions
#Other libs
import utime as time          # For sleep functions
import machine as mac         # For hardware usage
from mqtt import MQTTClient   # For use of MQTT protocol to talk to Adafruit IO
import ubinascii              # Conversions between binary data and various encodings
from LoRaWAN import lora      # For use of LoRaWAN
import network                # For use for network connectivity

# --- Global variables ---
  
# Adafruit IO (AIO) configuration
AIO_SERVER = "io.adafruit.com"
AIO_PORT = 1883
AIO_LIGHT_FEED = "Laderlappen/feeds/wine-light"
AIO_TEMP_FEED = "Laderlappen/feeds/wine-temp"
AIO_HUM_FEED = "Laderlappen/feeds/wine-hum"
AIO_VIB_FEED = "Laderlappen/feeds/wine-vib"

# Create instance of Lora
lora = lora()

# Create a global variable for later use
global client

# Loop counter
counter = 0  

# --- Pin declarations ---

# Pin of the DHT
DHTpin = mac.Pin(12, mac.Pin.OUT, mac.Pin.PULL_DOWN)
sensor = DHT11(DHTpin)

# Pin of the photosensor
photoRes = mac.ADC(mac.Pin(26))

# Declare led-position
led = mac.Pin("LED", mac.Pin.OUT)   

# Declare vibration sensor
vibPin = mac.Pin(14, mac.Pin.IN, mac.Pin.PULL_UP)



# --- Network connection ---

# Will try to connect with LoraWAN n times (the parameter in connectLoraWAN), then Wifi if loraWAN fails.
def connectNetwork():
    status = connectLoraWAN(1)
    if status == 1:
        return
    else:
        print("Trying WIFI")
        connectWifi()

def connectLoraWAN(n):
    # Declare network variables
    DEV_EUI = cred.DevEUI
    APP_EUI = cred.AppEUI
    APP_KEY = cred.AppKey
    lora.configure(DEV_EUI, APP_EUI, APP_KEY)

    lora.startJoin()

    print("Start Join...")
    count = 0
    print("Joining...", end="")
    while count < n and not lora.checkJoinStatus():
        print("." , end="")
        flashLed(1)
        count += 1
        time.sleep(1)
    if lora.checkJoinStatus():    
        print("Join success!")
        return 1
    else:
        print("\nFailed to join LoraWAN.")
        return 0

def connectWifi():
    wlan = network.WLAN(network.STA_IF)         # Put modem on Station mode
    if not wlan.isconnected():                  # Check if already connected
        print('connecting to network...')
        wlan.active(True)                       # Activate network interface
        # set power mode to get WiFi power-saving off (if needed)
        wlan.config(pm = 0xa11140)
        wlan.connect("NETGEAR16", "kindlake161")  # Your WiFi Credential
        print('Waiting for connection...', end='')
        # Check if it is connected otherwise wait
        while not wlan.isconnected() and wlan.status() >= 0:
            print('.', end='')
            time.sleep(1)
    # Print the IP assigned by router
    ip = wlan.ifconfig()[0]
    print('\nConnected on {}'.format(ip))
    return

# --- Sensor reading functions ---

# Function for getting vibration readings, triggers if vibration detected
def vibration():
   print('Vibration sensed')
   connectAdaFruit()
   client.publish(topic=AIO_VIB_FEED, msg="1")
   disconnectAdaFruit()
   flashLed(3)
   time.sleep(3)


# Function for getting light readings
def getLight():
    try:
        
        light = photoRes.read_u16()
        lightPerc = round(light / 65535 * 100, 2)
    except:
        print("An exception occured while getting light readings")
        return ""
    return lightPerc

# Function for getting temperature readings
def getDHT():
    try:
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
    except:
        print("An exception occured while getting temperature readings") 
        return ""
    return [t, h]

def getReadingsStr():
    lightp = getLight()
    dht = getDHT()
    print("Light: " + str(lightp))
    print("Temp & Hum:" + str(dht))
    global counter 
    counter += 1
    print("Cycle: " + str(counter))
    return [str(lightp), str(dht[1]), str(dht[0])]

# --- Publishing functions ---

# Function to publish sensor data to AdaFruit IO MQTT server
def publishData(readings = [2]):
    try:

        client.publish(topic=AIO_LIGHT_FEED, msg=readings[0])
        print("LIGHT DONE: " + readings[0])
        client.publish(topic=AIO_HUM_FEED, msg=readings[1])
        print("HUM DONE: " + readings[1])
        client.publish(topic=AIO_TEMP_FEED, msg=readings[2])
        print("TEMP DONE: " + readings[2])

    except Exception as e:
        print("FAILED: " + str(e))

def connectAdaFruit():

    # Subscribed messages will be delivered to this callback
    client.set_callback(sub_cb)
    client.connect()
    client.subscribe(AIO_LIGHT_FEED)
    client.subscribe(AIO_HUM_FEED)
    client.subscribe(AIO_TEMP_FEED)
    print("Connected to %s, subscribed to %s, %s and %s topics" % (AIO_SERVER, AIO_LIGHT_FEED, AIO_HUM_FEED, AIO_TEMP_FEED))

def disconnectAdaFruit():
    global client
    client.disconnect()
    print("Disconnected from Adafruit IO.")

def sub_cb(topic, msg):          # sub_cb means "callback subroutine"
    print((topic, msg))          # Outputs the message that was received. Debugging use.
    if msg == b"LIGHT":             
        client.publish(topic=AIO_LIGHT_FEED, msg=getLight()) 
    elif msg == b"HUMIDITY":      
        DHT = getDHT()
        client.publish(topic=AIO_LIGHT_FEED, msg=DHT[1])       
    elif msg == b"TEMPERATURE":
        DHT = getDHT()
        client.publish(topic=AIO_LIGHT_FEED, msg=DHT[0])

    else:                        # If any other message is received ...
        print("Unknown message") # ... do nothing but output that it happened.

#Flashes led n amount of times
def flashLed(integer):
    for x in range(integer):
        led.toggle()
        time.sleep(0.1)
        led.toggle()


# --- Main ---
def main():
    # Adafruit IO (AIO) configuration

    AIO_USER = cred.IO_USERNAME
    AIO_KEY = cred.IO_KEY
    AIO_CLIENT_ID = ubinascii.hexlify(mac.unique_id())  # Can be anything


    connectNetwork()
    # For getting vibration readings, triggers if vibration detected.
    #MQTT client variable
    global client
    # Use the MQTT protocol to connect to Adafruit IO
    client = MQTTClient(AIO_CLIENT_ID, AIO_SERVER, AIO_PORT, AIO_USER, AIO_KEY)

    #Create trigger mechanism for vibration sensor
    vibPin.irq(trigger=mac.Pin.IRQ_FALLING, handler=vibration())


    while True:
        try:
            #Connect to AdaFruit
            connectAdaFruit()
            # Get a list of readings in Str-format and use them as a parameter for publishing 
            publishData(getReadingsStr())
            #Flash led to note sending of data
            flashLed(1)

        # Exception handler 
        except Exception as e:
            print("Something went wrong: %s" % (e))

        #Disconnect from client and clean up. Sleep for 120 min.
        finally:
            disconnectAdaFruit()
            time.sleep(6120)

main()
