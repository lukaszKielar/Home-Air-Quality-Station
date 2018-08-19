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
To avoid problems with pin definition, Serial1 pins
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
#include "SSD1306Wire.h"
#include <RTClib.h>
#include "Adafruit_BME280.h"  
#include "PMS.h"

HardwareSerial Serial1(1);

#define ALTITUDE 219.0  // altitude in Krakow, Poland
#define I2C_SDA 21
#define I2C_SCL 22
#define BME280_ADDRESS 0x76
/* 
If the sensor does not work, try the 0x77 address as well
or try to scan your connection with i2c scanner
*/

PMS pms(Serial);  // PMS7003 sensor instance
PMS::DATA data;

Adafruit_BME280 bme(I2C_SDA, I2C_SCL);  // BME280 sensor instance

/*
Initialize the OLED display using Wire library
display(0x3c, SDA, SCL) (optional)
*/
SSD1306Wire display(0x3c, 21, 22);

RTC_DS3231 rtc;

char rtcDay[20];
char rtcMonth[20];
char rtcYear[20];
char rtcHour[20];
char rtcMinute[20];
char rtcSecond[20];

void setup()
{
  delay(3000);  // wait 3 seconds till program begins
  Serial.begin(9600);  // GPIO1, GPIO3 (ESP32 TX/RX pins)
  Serial1.begin(9600);  // GPIO2 (ESP32 D2 pin)

  // Initialising the UI will init the display too.
  display.init();

  display.flipScreenVertically();
  display.setFont(ArialMT_Plain_10);

  if (!rtc.begin()) 
  {
    Serial1.println("Couldn't find RTC");
    while (1);
  }

  Serial1.println("Time setting!");
  // following line sets the RTC to the date & time this sketch was compiled
  rtc.adjust(DateTime(F(__DATE__), F(__TIME__)));
  // manual time adjust
  // rtc.adjust(DateTime(2014, 1, 21, 3, 0, 0));

  initSensor();  // BME280 sensor initialization
}

void loop()
{
  String rtcString = returnDatetime();

  // print date & time using serial monitor
  Serial1.println(rtcString);
  
  // clear the display
  display.clear();

  // write date & time to oled display
  display.setTextAlignment(TEXT_ALIGN_LEFT);
  display.drawString(0, 0, rtcString);
  display.drawHorizontalLine(0, 15, display.getStringWidth(rtcString));
  
  Serial1.println("Data:");

  // check BME280 readings and write it to the display and serial monitor
  readBME();
  // check PMS7003 readings and write it to the display and serial monitor
  readPMS();

  display.drawString(0, 80, "Home Air Monitoring Station");
  
  Serial1.println();
//  delay(60000);  // wait 1 minute
  display.display();
  delay(1000);
}


void initSensor()
{
  bool status = bme.begin(BME280_ADDRESS);
  if (!status) 
  {
    Serial1.println("Could not find a valid BME280 sensor, check wiring!");
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
    Serial1.print("Temperature (*C): ");
    Serial1.println(t);
    display.drawString(0, 20, "Temperature " + String(t) + " [*C]");
  }
  
  if (!isnan(h))
  {
    Serial1.print("Humidity (%): ");
    Serial1.println(h);
    display.drawString(0, 30, "Humidity " + String(h) + " [%]");
  }

  if (!isnan(p))
  {
    Serial1.print("Pressure (hPa): ");
    Serial1.println(p);
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

    Serial1.print("PM 1.0 (ug/m3): ");
    Serial1.println(data.PM_AE_UG_1_0);
    //display.drawString(0, 50, "PM 1.0 " + String(data.PM_AE_UG_1_0) + " [ug/m3]");

    Serial1.print("PM 2.5 (ug/m3): ");
    Serial1.println(data.PM_AE_UG_2_5);
    display.drawString(0, 50, "PM 2.5 " + String(data.PM_AE_UG_2_5) + " [ug/m3]");

    Serial1.print("PM 10.0 (ug/m3): ");
    Serial1.println(data.PM_AE_UG_10_0);
    //display.drawString(0, 70, "PM 10.0 " + String(data.PM_AE_UG_10_0) + " [ug/m3]");
  }
}


String returnDatetime()
{
  DateTime now = rtc.now();
  
  // TIME
  uint8_t intHour = now.hour();
  uint8_t intMinute = now.minute();
  uint8_t intSecond = now.second();
  snprintf (rtcHour, 20, "%.2i", intHour);
  snprintf (rtcMinute, 20, "%.2i", intMinute);
  snprintf (rtcSecond, 20, "%.2i", intSecond);
  
  //DATE
  uint8_t intDay = now.day();
  uint8_t intMonth = now.month();
  uint16_t intYear = now.year();
  snprintf (rtcDay, 20, "%.2i", intDay);
  snprintf (rtcMonth, 20, "%.2i", intMonth);
  snprintf (rtcYear, 20, "%.4i", intYear);

  String timeString = String(rtcHour) + ":" + String(rtcMinute) + ":" + String(rtcSecond);
  String dateString = String(rtcDay) + "-" + String(rtcMonth) + "-" + String(rtcYear);
  String rtcString = timeString + " " + dateString;

  return rtcString;
}

