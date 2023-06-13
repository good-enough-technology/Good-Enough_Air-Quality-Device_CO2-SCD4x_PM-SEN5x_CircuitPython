## Note update to be more reliable in case of Hard FAULTs
## - only seen once on one of 3 devices after a few days. Unrepeated. 
## ideally log previous errors to mqtt feed after rebooting and reconnect
## see https://gist.github.com/anecdata/cfc4c585406d17985885bfe3a1cc9c73
import microcontroller
import time
import alarm # for sleep memory
import board
import busio
from adafruit_io import adafruit_io_errors
from Adafruit_IO import *
from adafruit_io.adafruit_io_errors import AdafruitIO_RequestError, AdafruitIO_ThrottleError, AdafruitIO_MQTTError
from adafruit_io.adafruit_io import IO_MQTT
import os
import storage
import digitalio
import wifi
from adafruit_minimqtt.adafruit_minimqtt import MQTT, MMQTTException
import socketpool
import gc
import json
import traceback
import sys
import displayio
import terminalio
import adafruit_display_text.bitmap_label as Label
import adafruit_bitmap_font.bitmap_font as bitmap_font
import vectorio
import bitmaptools
from adafruit_display_shapes import *
import struct
from adafruit_scd4x import SCD4X
#from sensirion_i2c_scd import Scd4xI2cDevice
from sensirion_i2c_sen5x import Sen5xI2cDevice
from sensirion_i2c_driver import I2cTransceiver,I2cConnection

#from alarm import sleep_memory as sleep_memory
from microcontroller import nvm as sleep_memory

import adafruit_logging as logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# NOTE: Display rotation is best fixed in boot.py

import supervisor
from useful import *
# code.py is the entry point for RELOAD (software, REPL control-D, auto-reload, or run after reset)
# read and process safemode.json and boot.json if desired
# read and process boot_out.txt if desired (should have any traceback from boot.py, and any print() from boot.py, up to ~512 bytes)
# set up the run dict
run_dict = {}
run_dict["run_reason"] = str(supervisor.runtime.run_reason)
update_restart_dict_time(run_dict)  # add timestamp
update_restart_dict_traceback(run_dict)  # supervisor.get_previous_traceback
print("run info=",run_dict)

DATA_POINTS_PER_MINUTE = 20 # set to 30 if not paid adafruit IO plan
MAX_SENSOR_ERRORS_BEFORE_REBOOT = 10
NO_SLEEP_MEM=not bool(sleep_memory)
try:
    sleep_memory[SLEEP_MEMORY_ERROR] = 0x00
    sleep_memory[SLEEP_MEMORY_ERROR_SIZE:SLEEP_MEMORY_ERROR_SIZE+2] = bytearray([0x00,0x00])
except Exception as e:
    traceback.print_exception(e.__class__, e, e.__traceback__)
    print("Setting sleep Error: ",e)
    time.sleep(2)
    NO_SLEEP_MEM=True
    pass


try:
    #Setup boot toggle pin, also timer skip pin
    D2 = digitalio.DigitalInOut(board.D2)
    D2.direction = digitalio.Direction.INPUT
    D2.pull = digitalio.Pull.DOWN
    print("D2.value=",D2.value)

    # Read the Adafruit IO username and API key from the CircuitPython settings file
    aio_username = os.getenv('CIRCUITPY_AIO_USERNAME')
    aio_key = os.getenv('CIRCUITPY_AIO_KEY')

    # Define global variables to handle rate limits, throttling, and bans
    throttle_time = 0
    ban_time = 0
    is_throttling = False

    # displayio.release_displays()
    display = board.DISPLAY
    
    # setup displayio to have a main group that then has two sub groups, each occupying half the 240x135px screen. The lower section should be the TERMINAL output
    mainGroup = displayio.Group()
    display.root_group = mainGroup
    metricGroup = displayio.Group()
    metricGroup.y = 60
    metricGroup.x = 0
    metricGroup.scale = 1
    termialGroup = displayio.Group()
    termialGroup.y = 0
    termialGroup.x = 0
    termialGroup.scale = 1
    termialGroup.hidden = False
    termialGroup.append(displayio.CIRCUITPYTHON_TERMINAL)
    supervisor.reset_terminal(240, 72) #67 is half the screen height
    supervisor.status_bar.display = False
    supervisor.status_bar.display = True
    mainGroup.append(termialGroup)
    mainGroup.append(metricGroup)
    #add a label to displayio group
    font = terminalio.FONT
    try:
        font = bitmap_font.load_font("Inter-Thin-30.bdf")  # Load the font file
        font.load_glyphs(code_points='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890- ().,:!?/\\%+@~')
        font.load_glyphs('°³µ')  # pre-load glyphs for fast printing
    except:
        pass
    label = Label.Label(font, text="Good-\n\tEnough\n.technology")
    label.anchor_point = (0.5, 0.5)  # center the label
    label.anchored_position = (display.width // 2, metricGroup.y // 2)  # center the label
    label.line_spacing = 0.75
    label.background_tight = True

    palette = displayio.Palette(255)
    palette[0] = 0x125690
    palette[1] = 0xFF0000
    palette[2] = 0x00FF00
    palette[3] = 0x0000FF
    palette[5] = 0xFFFFFF
    palette[6] = 0x008800
    palette[7] = 0xCC0000
    palette[8] = 0xCCCC00
    for p in range(9, len(palette)):
        palette[p] = 0x000000
    palette.make_transparent(4)

    circle = vectorio.Circle(pixel_shader=palette, radius=25, x=26, y=40)
    circle.color_index = min(6, len(palette) - 1)
    metricGroup.append(circle)

    # rectangle = vectorio.Rectangle(pixel_shader=palette, width=40, height=30, x=55, y=45)
    # metricGroup.append(rectangle)

    # points=[(0, 0), (100, 20), (20, 20), (20, 100)]
    # polygon = vectorio.Polygon(pixel_shader=palette, points=points, x=0, y=0)
    # metricGroup.append(polygon)
    
    metricGroup.append(label)

    metric_display_counter = 0
    def update_display():
        global metric_display_counter
        global scd4x_device
        global sen5x_data
        global channel_total
        if channel_total == 0:
            #TODO: Add no channels msg or display animation for connecting sensors
            return
        metric_display_counter = metric_display_counter + 1
        if metric_display_counter > channel_total - 1 :
            metric_display_counter = metric_display_counter % channel_total
            if scd4x_device is None:
                metric_display_counter += 3
                
             # channel_total
        # if channel_total == 8: 
        #     metric_display_counter = metric_display_counter + 3
        if scd4x_device:
            if metric_display_counter == 0:
                displayMetric("CO2", scd4x_device.CO2, "ppm")
            elif metric_display_counter == 1:
                displayMetric("Temp", scd4x_device.temperature, "°C")
            elif metric_display_counter == 2:
                displayMetric("Humidity", scd4x_device.relative_humidity, "%")
        if sen5x_device:
            if metric_display_counter == 3:
                displayMetric("PM1", sen5x_data.mass_concentration_1p0.physical, "µg/m³")
            elif metric_display_counter == 4:
                displayMetric("PM2.5", sen5x_data.mass_concentration_2p5.physical, "µg/m³")
            elif metric_display_counter == 5:
                displayMetric("PM4", sen5x_data.mass_concentration_4p0.physical, "µg/m³")
            elif metric_display_counter == 6:
                displayMetric("PM10", sen5x_data.mass_concentration_10p0.physical, "µg/m³")
            elif metric_display_counter == 7:
                displayMetric("Temp", sen5x_data.ambient_temperature.degrees_celsius, "°C")
            elif metric_display_counter == 8:
                displayMetric("Humidity", sen5x_data.ambient_humidity.percent_rh, "%")
            elif metric_display_counter == 9:
                displayMetric("VOC", sen5x_data.voc_index.scaled, "(100~=0)")
            elif metric_display_counter == 10:
                displayMetric("NOx", sen5x_data.nox_index.scaled, "(1~=0)")

    def displayMetric(metric_name, metric_value, unit):
        global metricGroup
        global metric_display_counter
        global label
        if metric_value is None or str(metric_value).lower() is 'nan':
            update_display()
        else:
            label.text = metric_name + ":\n" + str(metric_value) + " " + unit

    
    transparent_sprite = None
    
    def alpha_label():
        global label
        global metricGroup
        global mainGroup
        global palette
        global transparent_sprite
        background_bitmap = displayio.Bitmap(label.bitmap.width, label.bitmap.height, len(palette))
        color = len(palette)-1
        for i,c in enumerate(palette):
            if palette.is_transparent(i):
                color = i
                break
        for x in range(label.bitmap.width):
            for y in range(label.bitmap.height):
                background_bitmap[x, y] = color
        # transparent_bitmap = displayio.Bitmap(240, 135, 1)
        try:
            metricGroup.remove(transparent_sprite)
        except:
            pass
        result_bitmap = displayio.Bitmap(label.bitmap.width, label.bitmap.height, len(palette))
        print("result_bitmap: (",result_bitmap.width,",",result_bitmap.height,")")
        print("label.bitmap: (",label.bitmap.width,",",label.bitmap.height,")")
        print("background_bitmap: (",background_bitmap.width,",",background_bitmap.height,")")

        
        bitmaptools.alphablend(result_bitmap, label.bitmap, background_bitmap, displayio.Colorspace.RGB565, 0.65, 0.35)
        transparent_sprite = displayio.TileGrid(result_bitmap, pixel_shader=palette, x=0, y=0)

        metricGroup.append(transparent_sprite)
        # Create a new bitmap with the transparent color
    #alpha_label()

    class Sen5xProductType:
        SPS30 = "SPS30"
        SEN50 = "SEN50"
        SEN54 = "SEN54"
        SEN55 = "SEN55"


    # Callback function for 'tyeth/throttle' topic
    def on_throttle(client, topic, message):
        global throttle_time
        global is_throttling
        try:
            new_throttle_time = float(message.split(',')[1].split()[0])
            if new_throttle_time > throttle_time:
                throttle_time = new_throttle_time
                print("Throttle message received: ", message)
            print("Throttle message received: ", message)
        except ValueError as e:
            throttle_time = 15
            print("Error parsing throttle message: ", message)
        is_throttling = True

    def postToAdafruitIOAndDoThrottleWait():
        global throttle_time
        global is_throttling
        global D2
        global aio_client
        try:
            aio_client.loop(0)
        except Exception as e:
            print("MQTT Error: ",e)
            #TODO: setup run_dict with timestamp, reboot reason (e), traceback, and log to running.json
            print("Rebooting via exception logger in 1.5secs...")
            time.sleep(1.5)
            raise e
        finally:
            if(is_throttling):
                for k in range(throttle_time):
                    print(f"Throttling data for {throttle_time} seconds")
                    time.sleep(0.5)
                    update_display()
                    if D2.value == True:
                        print("Throttle cancelled")
                        throttle_time = 0
                        is_throttling = False
                        break
                    time.sleep(0.5)
                    throttle_time = throttle_time - 1 if throttle_time > 0 else 0
                is_throttling = False


    # Callback function for 'tyeth/errors' topic
    def on_ban(client, topic, message):
        global ban_time
        if(message.find("ban")):
            ban_time = float(message.split()[-2])
            print("Ban (",ban_time,"s) message received: ", message)
            print("Ban: Sleeping for ",ban_time,"s")
            for i in range(int(ban_time)):
                update_display()
                time.sleep(1)
            print("Done sleeping due to ban")
        else:
            print("Error message received on topic (",topic,"): ", message)
            time.sleep(300)

    def doReconnectWifi():
        if(wifi.radio.connected==False):
            print("Reconnecting to WiFi...")
            print("Disabling WiFi radio...")
            wifi.radio.enabled = False
            time.sleep(1)
            print("Enabling WiFi radio...")
            wifi.radio.enabled = True
            time.sleep(1)
            print("Connecting to WiFi...")
            wifi.radio.connect(os.getenv('CIRCUITPY_WIFI_SSID'), os.getenv('CIRCUITPY_WIFI_PASSWORD'))
            i=0
            while not wifi.radio.connected:
                print(".")
                time.sleep(1)
                i+=1
                if i>30:
                    print("Rebooting due to WiFi connection timeout")
                    time.sleep(1)
                    raise Exception("WiFi connection timeout")
        

    # pylint: disable=unused-argument
    def disconnected(client):
        # Disconnected function will be called when the client disconnects.
        print("Disconnected from Adafruit IO!")
        time.sleep(1)
        doReconnectWifi()
        print("Reconnecting to Adafruit IO...")
        client.reconnect()

    # pylint: disable=unused-argument
    def message(client, feed_id, payload):
        # Message function will be called when a subscribed feed has a new value.
        # The feed_id parameter identifies the feed, and the payload parameter has
        # the new value.
        print("Feed {0} received new value: {1}".format(feed_id, payload))


    # Function to convert MAC address bytes to a string
    def bytes_to_mac_string(mac_bytes):
        return ':'.join(['{:02X}'.format(byte) for byte in mac_bytes])

    # Get the MAC address as a string
    mac_address = bytes_to_mac_string(wifi.radio.mac_address)

    def check_wifi_status_and_print_connecting_dots_then_reboot():
        # elif status == wifi.WiFiState.IDLE:
        #     print("Wi-Fi idle")
        #     print("Connecting to Wi-Fi")
        # elif status == wifi.WiFiState.CONNECTED:
        # elif status == wifi.WiFiState.DISCONNECTED:
        if wifi.radio.connected:
            print("Connected to Wi-Fi")
            return True
        else:
            doReconnectWifi()
            return True

    check_wifi_status_and_print_connecting_dots_then_reboot()
    
    boardname = board.board_id if hasattr(board, "board_id") else "UnknownBoard"
    group_name = mac_address.replace(":", "") + "-" + boardname.replace("_", "-").replace("adafruit-feather", "AfF").replace("reverse","rev")

    # Set up the MQTT client
    mqtt_client = MQTT(
        broker="io.adafruit.com",
        port=1883,
        username=aio_username,
        password=aio_key,
        client_id=group_name,
        socket_pool=socketpool.SocketPool(wifi.radio),
    )
    print("Connecting to Adafruit IO MQTT broker...")

    # Pass the MQTT client to the IO_MQTT constructor
    aio_client = IO_MQTT(mqtt_client)
    i=0
    while True:
        i=i+1
        try:
            aio_client.connect()
            aio_client.subscribe_to_errors()
            aio_client.subscribe_to_throttling()
            aio_client.on_message = message
            aio_client.on_disconnect = disconnected

            mqtt_client.add_topic_callback(f'{aio_username}/errors', on_ban)
            mqtt_client.add_topic_callback(f'{aio_username}/throttle', on_throttle)

            print('Connected to Adafruit IO!')
            break
        except Exception as e:
            if(i>20):
                raise e
            print("Failed to connect, retrying\n", e)
            time.sleep(10)


    # Set up the I2C buses
    #TODO: fix this as not working as expected, board defines STEMMA_i2c as i2c :-(
    #i2c_buses = [board.I2C(), board.STEMMA_I2C()] if hasattr(board, "STEMMA_I2C") and board.I2C != board.STEMMA_I2C else [board.I2C()]
    #print(i2c_buses)
    
    #ESP32-S2 and S3 have bug with base i2c speed of 100kHz not clock stretching correctly and adding 10ms delay to every i2c command
    i2c_buses = [busio.I2C(board.SCL, board.SDA, frequency=125000)]
    
    # Define feed names
    feed_names = {
        "scd4x": {
            "co2": group_name + "-scd4x-co2",
            "temperature": group_name + "-scd4x-temperature",
            "humidity": group_name + "-scd4x-humidity",
        },
        "sen5x": {
            "ppm-1": group_name + "-sen5x-ppm-1",
            "ppm-2.5": group_name + "-sen5x-ppm-2.5",
            "ppm-4": group_name + "-sen5x-ppm-4",
            "ppm-10": group_name + "-sen5x-ppm-10",
            "temperature": group_name + "-sen5x-temperature",
            "humidity": group_name + "-sen5x-humidity",
            "voc": group_name + "-sen5x-voc",
            "nox": group_name + "-sen5x-nox",
        },
    }

    # Discover SCD4x and SEN5x devices on I2C buses
    scd4x_device = None
    sen5x_device = None

    SCD4X_DEFAULT_ADDRESS = 0x62
    SEN5X_DEFAULT_ADDRESS = 0x69

    for i2c in i2c_buses:
        try:
            scd4x_device = SCD4X(i2c, SCD4X_DEFAULT_ADDRESS)
            print(f"SCD4x device found on I2C bus {i2c}, fetching serial#")
            time.sleep(1)
            print(f"Serial #{scd4x_device.serial_number}")
            print("Attempting to take first reading after starting measurements")
            scd4x_device.self_calibration_enabled = False
            ## use openapi for elevation using config lat/long, which is also used for data feeds if present, allows detecting worse air outside.
            # See Particulate Matter API https://app.noteable.io/f/8453150c-f579-4298-a9dc-390789ebc17d/OpenAQ_API_Bristol_AirQuality.ipynb
            # And Open Elevation API https://app.noteable.io/f/0beef108-1273-4deb-bd81-937b948eb449/Elevation-APIs.ipynb
            scd4x_device.altitude = 38 # move to config file
            # scd4x_device.temperature_offset = 0
            scd4x_device.persist_settings()

            scd4x_device.start_periodic_measurement()
            time.sleep(1)
            if scd4x_device.data_ready:
                print("data ready, continuing.")
            else:
                print("scd4x data NOT ready!")
                scd4x_errors=1
            break
        except (OSError,ValueError):
            print("SCD4x sensor not detected")
            continue

    sen5x_product = "SEN5x"
    for i2c in i2c_buses:
        try:
            
            transceiver = I2cTransceiver(i2c, SEN5X_DEFAULT_ADDRESS)
            sen5x_device = Sen5xI2cDevice(I2cConnection(transceiver))
            print("SEN5x initialised, resetting, waiting 1.1 seconds before read")
            sen5x_device.device_reset()
            time.sleep(1.1)
            # sen5x_device = Sen5xI2cDevice(i2c, SEN5X_DEFAULT_ADDRESS)
            sen5x_product = sen5x_device.get_product_name()
            print(f"SEN5x device found on I2C bus {i2c}, product type: {sen5x_product}, #{sen5x_device.get_serial_number()}")
            sen5x_device.start_measurement()
            break
        except (OSError,ValueError):
            print("SEN5x sensor not detected")
            continue

    scd4x_errors = 0
    sen5x_errors = 0

    # Loop forever, reading the sensor data and publishing it to Adafruit IO
    while True:
        # wait for datapoints total to not flood rate limit of 30 per minute
        channel_total = 0 # Number of data points (3 for SCD4x, 4 for SEN50)
        
        try:
            gc.collect()
            if scd4x_device:
                try:
                    scd4x_publish = False
                    if not scd4x_device.data_ready:
                        print("SCD4x data not ready, reattempting for 30sec")
                        start_time = time.monotonic_ns()
                        while time.monotonic_ns() - start_time < 30*1000000000:
                            if scd4x_device.data_ready:
                                scd4x_publish = True
                                break
                            time.sleep(0.2)
                    else:
                        scd4x_publish = True
                    if not scd4x_publish and not scd4x_device.data_ready:
                        print("SCD4x data not ready, running self_test")
                        time.sleep(0.1)
                        scd4x_device.self_test()
                        print("Restarting SCD4x measurements")
                        scd4x_device.start_periodic_measurement()
                        print("Measurements restarted successfully, waiting 2seconds")
                        time.sleep(1)
                        start_time = time.monotonic_ns()
                        while time.monotonic_ns() - start_time < 1000000000:
                            if scd4x_device.data_ready:
                                scd4x_publish = True
                                break
                            time.sleep(0.2)
                    if scd4x_publish:
                        print(f"Publishing SCD4X data: CO2: {scd4x_device.CO2}, Temperature: {scd4x_device.temperature}, Humidity: {scd4x_device.relative_humidity}")
                        aio_client.publish(feed_names["scd4x"]["co2"], scd4x_device.CO2)
                        aio_client.publish(feed_names["scd4x"]["temperature"], scd4x_device.temperature)
                        aio_client.publish(feed_names["scd4x"]["humidity"], scd4x_device.relative_humidity)
                        scd4x_errors = 0
                        channel_total += 3
                    else:
                        print("SCD4x data not ready, skipping publish(errors+1)")
                        scd4x_errors+=1
                except OSError as e:
                    print("SCD4x Error: ",e)
                    scd4x_errors+=1
            postToAdafruitIOAndDoThrottleWait()
            time.sleep(1)
            update_display()
            if sen5x_device:
                try:
                    if sen5x_device.read_data_ready():
                        sen5x_data = sen5x_device.read_measured_values()
                        print(f"Publishing {sen5x_product} data: PM1.0: {sen5x_data.mass_concentration_1p0.physical}, PM2.5: {sen5x_data.mass_concentration_2p5.physical}, PM4.0: {sen5x_data.mass_concentration_4p0.physical}, PM10: {sen5x_data.mass_concentration_10p0.physical}",end="")
                        aio_client.publish(feed_names["sen5x"]["ppm-1"], sen5x_data.mass_concentration_1p0.physical)
                        aio_client.publish(feed_names["sen5x"]["ppm-2.5"], sen5x_data.mass_concentration_2p5.physical)
                        aio_client.publish(feed_names["sen5x"]["ppm-4"], sen5x_data.mass_concentration_4p0.physical)
                        aio_client.publish(feed_names["sen5x"]["ppm-10"], sen5x_data.mass_concentration_10p0.physical)
                        postToAdafruitIOAndDoThrottleWait()
                        channel_total += 4  

                        if sen5x_product in (Sen5xProductType.SPS30, Sen5xProductType.SEN54, Sen5xProductType.SEN55):
                            print(f" VOC: {sen5x_data.voc_index.scaled} Temp: {sen5x_data.ambient_temperature.degrees_celsius} Humidity: {sen5x_data.ambient_humidity.percent_rh}",end="")
                            aio_client.publish(feed_names["sen5x"]["voc"], sen5x_data.voc_index.scaled)
                            aio_client.publish(feed_names["sen5x"]["temperature"], sen5x_data.ambient_temperature.degrees_celsius)
                            aio_client.publish(feed_names["sen5x"]["humidity"], sen5x_data.ambient_humidity.percent_rh)
                            postToAdafruitIOAndDoThrottleWait()
                            channel_total += 3

                        if sen5x_product == Sen5xProductType.SEN55:
                            print(f" NOx: {sen5x_data.nox_index.scaled}", end=" ")
                            aio_client.publish(feed_names["sen5x"]["nox"], sen5x_data.nox_index.scaled)
                            postToAdafruitIOAndDoThrottleWait()
                            channel_total += 1
                        print("||",end=" ")
                    else:
                        print("SEN5x data not ready, fan cleaning interval: ",sen5x_device.get_fan_auto_cleaning_interval(),"s",sep="")
                except OSError as e:
                    print("SEN5x Error: ",e)
                    sen5x_errors+=1

        except MMQTTException as e:
            print("MQTT Error: ",e)
            print("Rebooting via exception logger...")
            time.sleep(1.5)
            raise e
            microcontroller.reset()

        # If we've had 5 errors in a row, reboot
        if (scd4x_device and scd4x_errors >= MAX_SENSOR_ERRORS_BEFORE_REBOOT) or (sen5x_device and sen5x_errors >= MAX_SENSOR_ERRORS_BEFORE_REBOOT):
            print("Too many sensor errors, scd:",scd4x_errors," sen:",sen5x_errors,", rebooting...")
            time.sleep(1.5)
            raise Exception("Too many sensor errors, scd4x:",scd4x_errors," sen5x:",sen5x_errors,", rebooting...")
            microcontroller.reset()
        

        if channel_total > 0:
            circle.color_index = 6 # green
            
            def do_color_PM(value, displayItemWithColorIndex, mid=50, high=100):
                if value is None or value == 'NaN' or value == "nan":
                    return
                if value > high:
                    displayItemWithColorIndex.color_index = 7 # red
                elif value > mid:
                    if displayItemWithColorIndex.color_index == 6:
                        displayItemWithColorIndex.color_index = 8 # yellow
            
            if scd4x_device:
                do_color_PM(scd4x_device.CO2,circle, mid=1000, high=1500)
            
            if sen5x_device:
                do_color_PM(sen5x_data.mass_concentration_1p0.physical,circle)
                do_color_PM(sen5x_data.mass_concentration_2p5.physical,circle)
                do_color_PM(sen5x_data.mass_concentration_4p0.physical,circle)
                do_color_PM(sen5x_data.mass_concentration_10p0.physical,circle)
                if sen5x_product in (Sen5xProductType.SPS30, Sen5xProductType.SEN54, Sen5xProductType.SEN55):
                    do_color_PM(sen5x_data.voc_index.scaled,circle, mid=150, high=200)
                if sen5x_product == Sen5xProductType.SEN55:
                    do_color_PM(sen5x_data.nox_index.scaled,circle, mid=5, high=10)
            
        # Wait at least for a short time before reading the sensor data again in case datapoint logic is broken
        time.sleep(0.5)
        
        datapoints_per_minute = 1 if channel_total > DATA_POINTS_PER_MINUTE else DATA_POINTS_PER_MINUTE / channel_total if channel_total > 0 else 30 # wait 2 seconds at startup fpr sensors to warm up
        sleep_time = int(60 / datapoints_per_minute)
        metric_seconds_counter = 0
        print('Sleeping', sleep_time, 'seconds for', channel_total, 'datapoints')
        for k in range(sleep_time):
            time.sleep(1)
            metric_seconds_counter = (metric_seconds_counter + 1) % 2
            if metric_seconds_counter == 0:
                update_display()
            if D2.value == True:
                circle.color_index=(circle.color_index+1) % len(palette)
                print("Sleep cancelled")
                break
        #TODO: use screensaver every x interrations

    ################### End of Code ###################
except Exception as e:
    print("Error: ",e)
    time.sleep(1)
    # Get the current time
    timestamp = time.monotonic()

    # Get the traceback
    errorlines = traceback.format_exception(e.__class__, e, e.__traceback__)
    tb_str = ''.join(errorlines)

    # Create the error dictionary
    error = {
        'timestamp': timestamp,
        'exception': str(e),
        'traceback': tb_str
    }
    data = json.dumps(error)
    # Append the error to errors.json
    # with open('/errors.json', 'a') as f:
    #     json.dump(error, f)
    if(NO_SLEEP_MEM):
        print("rebooting, unable to save error-reason to sleep memory")
        time.sleep(1)
    else:
        data = data[:len(sleep_memory)-SLEEP_MEMORY_ERROR_REASON] # truncate to fit in sleep memory
        if(len(data)>0):
            print("saving error-reason to sleep memory: ",data)
            sleep_memory[SLEEP_MEMORY_ERROR] = 1
            data = bytes(data, 'utf-8')
            data = data[:len(sleep_memory)-SLEEP_MEMORY_ERROR_REASON]
            sleep_memory[SLEEP_MEMORY_ERROR_SIZE:SLEEP_MEMORY_ERROR_SIZE+2] = struct.pack("H",len(data))
            sleep_memory[SLEEP_MEMORY_ERROR_REASON:len(data)+SLEEP_MEMORY_ERROR_REASON] = data  ## [:len(sleep_memory)-SLEEP_MEMORY_ERROR_REASON]
            print("done")
            time.sleep(2)

        # # pad rest with zeros
        # for i in range(len(sleep_memory)-len(sleep_memory[SLEEP_MEMORY_ERROR_REASON])):
        #     sleep_memory[SLEEP_MEMORY_ERROR_REASON+i] = 0

    # Reset the microcontroller
    # print("supervisor.reload()")
    print("microcontroller.reset()")
    time.sleep(2)
    # microcontroller.on_next_reset(microcontroller.RunMode.SAFE_MODE)
    # supervisor.reload()
    microcontroller.reset()
