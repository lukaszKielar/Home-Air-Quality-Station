/*
Home Air Quality Station
Copyright 2018, Łukasz Kielar, All rights reserved.
https://github.com/lukaszKielar

Project allows to measure basic air parameters such as temperature, humidity, pressure
and particulate matter concentration (1, 2.5 and 10 um).
Monitoring station was built using
  DOIT ESP32 DevKit v1
  Plantower PMS7003 particulate matter sensor
  BME280 tempetarure, humidity and pressure sensor
  SSD1306 OLED Screen (optional)
  DS3231 Real Time Clock (optional)

Following libraries was used for this project
  https://github.com/Takatsuki0204/BME280-I2C-ESP32
  https://github.com/fu-hsi/PMS
  https://github.com/ThingPulse/esp8266-oled-ssd1306 (optional)
  https://github.com/adafruit/RTClib (optional)

DOIT ESP32 DEVKIT V1 PIN DEFINITION: 
  SDA - 21
  SCL - 22

Notes:
To avoid problems with pin definition, Serial2 pins
have been changed from 9, 10 to 4, 2 in HardwareSerial.cpp

To make sure I2C addresses were parsed correctly you can use
I2C scanner sketch available on github
  https://gist.github.com/tfeldmann/5411375
By default sensors uses following i2c addresses:
  BME280  - 0x76
  SSD1306 - 0x3c
  RTC DS3231  - 0x68
*/

#include <Wire.h>
#include <SSD1306Wire.h>
#include <RTClib.h>
#include <Adafruit_BME280.h>
#include <PMS.h>
#include <PubSubClient.h>
#include <WiFiMulti.h>
#include "wifi_config.h"

//HardwareSerial Serial2(2);

#define ALTITUDE 219.0  // altitude in Cracow, Poland
#define I2C_SDA 21
#define I2C_SCL 22
#define BME280_ADDRESS 0x76
/* 
If the sensor does not work, try the 0x77 address as well
or try to scan your connection with i2c scanner
*/

WiFiClient espClient;  // PubSubClient instance
PubSubClient client(espClient);

WiFiMulti WiFiMulti;

PMS pms(Serial);  // PMS7003 sensor instance
PMS::DATA data;

Adafruit_BME280 bme(I2C_SDA, I2C_SCL);  // BME280 sensor instance

/*
Initialize the OLED display using Wire library
display(0x3c, SDA, SCL) (optional)
*/
SSD1306Wire display(0x3c, 21, 22);

RTC_DS3231 rtc;

char rtc_day[20];
char rtc_month[20];
char rtc_year[20];
char rtc_hour[20];
char rtc_minute[20];
char rtc_second[20];

long last_msg = 0;
char pm1pt_msg[20];
char pm2pt5_msg[20];
char pm10pt_msg[20];    
char temp_msg[20];
char humid_msg[20];
char pressure_msg[20];

void setup()
{
  delay(3000);  // wait 3 seconds till program begins
  Serial.begin(9600);  // GPIO1, GPIO3 (ESP32 TX/RX pins)
  Serial2.begin(9600);  // GPIO2 (ESP32 D2 pin)

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  // Initialising the UI will init the display too.
  display.init();

  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_10);

  if (!rtc.begin()) 
  {
    Serial2.println("Couldn't find RTC");
    while (1);
  }
    
  if (rtc.lostPower())
  {
    Serial2.println("Time setting!");
    // following line sets the RTC to the date & time this sketch was compiled
    rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
    // manual time adjust
    // rtc.adjust(DateTime(2014, 1, 21, 3, 0, 0));
  }

  initBME280();  // BME280 sensor initialization

  connectWifi();

  //Configure MQTT server
  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(receivedCallback);
}

void loop()
{

  if (!client.connected())
  {
    connectMqtt();
  }

  client.loop();
  
  String rtc_string = returnDatetime();
  Serial2.println(rtc_string);  // print date & time using serial monitor
  
  display.clear();  // clear the display

  // write date & time to oled display
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.drawString(0, 0, rtc_string);
  display.drawHorizontalLine(0, 15, display.getStringWidth(rtc_string));
  
  Serial2.println("Data:");
  readBME();  // write BME280 readings to the display and serial monitor
  readPMS();  // write PMS7003 readings to the display and serial monitor

  display.drawString(0, 80, "Home Air Monitoring Station");
  
  Serial2.println();
  // delay(60000);  // wait 1 minute
  display.display();
  delay(1000);
}


void initBME280()
{
  bool status = bme.begin(BME280_ADDRESS);
  if (!status) 
  {
    Serial2.println("Could not find a valid BME280 sensor, check wiring!");
    while (1);
  }
}


void readBME()
{
  float t = bme.readTemperature();
  float h = bme.readHumidity();
  float p = bme.readPressure();
  p = bme.seaLevelForAltitude(ALTITUDE,p);
  p = p/100.0F;

  if (!isnan(t))
  {
    Serial2.print("Temperature (*C): ");
    Serial2.println(t);
    display.drawString(0, 20, "Temperature " + String(t) + " [*C]");
  }
  
  if (!isnan(h))
  {
    Serial2.print("Humidity (%): ");
    Serial2.println(h);
    display.drawString(0, 30, "Humidity " + String(h) + " [%]");
  }

  if (!isnan(p))
  {
    Serial2.print("Pressure (hPa): ");
    Serial2.println(p);
    display.drawString(0, 40, "Pressure " + String(p) + " [hPa]");
  }
}


void readPMS()
{
  if (pms.readUntil(data, 5000))
  {
    uint16_t pm1 = data.PM_AE_UG_1_0;
    uint16_t pm2_5 = data.PM_AE_UG_2_5;
    uint16_t pm10 = data.PM_AE_UG_10_0;

    Serial2.print("PM 1.0 (ug/m3): ");
    Serial2.println(data.PM_AE_UG_1_0);
    //display.drawString(0, 50, "PM 1.0 " + String(data.PM_AE_UG_1_0) + " [ug/m3]");

    Serial2.print("PM 2.5 (ug/m3): ");
    Serial2.println(data.PM_AE_UG_2_5);
    display.drawString(0, 50, "PM 2.5 " + String(data.PM_AE_UG_2_5) + " [ug/m3]");

    Serial2.print("PM 10.0 (ug/m3): ");
    Serial2.println(data.PM_AE_UG_10_0);
    //display.drawString(0, 70, "PM 10.0 " + String(data.PM_AE_UG_10_0) + " [ug/m3]");
  }
}


String returnDatetime()
{
  DateTime now = rtc.now();
  
  // TIME
  uint8_t int_hour = now.hour();
  uint8_t int_minute = now.minute();
  uint8_t int_second = now.second();
  snprintf (rtc_hour, 20, "%.2i", int_hour);
  snprintf (rtc_minute, 20, "%.2i", int_minute);
  snprintf (rtc_second, 20, "%.2i", int_second);
  
  //DATE
  uint8_t int_day = now.day();
  uint8_t int_month = now.month();
  uint16_t int_year = now.year();
  snprintf (rtc_day, 20, "%.2i", int_day);
  snprintf (rtc_month, 20, "%.2i", int_month);
  snprintf (rtc_year, 20, "%.4i", int_year);

  String time_string = String(rtc_hour) + ":" + String(rtc_minute) + ":" + String(rtc_second);
  String date_string = String(rtc_day) + "-" + String(rtc_month) + "-" + String(rtc_year);
  String rtc_string = time_string + " " + date_string;

  return rtc_string;
}


void receivedCallback(char* topic, byte* payload, unsigned int length)
{
  Serial2.println("Message recieved: ");
  Serial2.println(topic);
  Serial2.print("payload: ");
  for(int i = 0; i<length; i++)
  {
    Serial2.print((char)payload[i]);
  }
  Serial2.println();
}


void connectMqtt()
{
  while (!client.connected())
  {
    Serial2.println("MQTT connecting ...");
    
    if (client.connect("ESP32 Client", MQTT_USER, MQTT_PASSWORD))
    {
      Serial2.println("Connected to MQTT");
    }
    else
    {
      Serial2.println("ERROR. Failed with state ");
      Serial2.print(client.state());
      
      Serial2.println("Try again in 2 seconds");
      delay(2000);
    }
  }
}


void connectWifi()
{
  WiFiMulti.addAP(WIFI_SSID, WIFI_PASSWORD);  // We start by connecting to a WiFi network

  Serial2.println("Wait for WiFi... ");
  while (WiFiMulti.run() != WL_CONNECTED)
  {
    Serial2.print(".");
    delay(500);
  }
  Serial2.println("WiFi connected");
  Serial2.print("IP address: ");
  Serial2.println(WiFi.localIP());
}
