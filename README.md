# Alfred

## About
Alfred is a home automation web app based on Tornado and designed to run on Raspberry Pi.

## Hardware
Some hardware used:  
 - RPi with picamera for video surveillance using [picamweb](https://github.com/iticus/picamweb) project (jsmpg+websockets)  
 - ESP8266 wifi module for power (switch) control and temperature/humidity readings  
 - 433 Mhz radio module connected to RPi for power socket/light bulb control  
 - basic speaker for playing audio  

## Functions
The application supports the following concepts:  
 - *sensors* (to display data such as temperature)  
 - *switches* (to control state with support for defining schedules)  
 - *sounds* (to play audio)  
 - *cameras* (to show live streams)  
The application can detect offline signals and notify the user using web push notifications.  

## Screenshots
### Switch
![Switch](http://iticus.ro/static/img/switch.png)
### Sound
![Sound](http://iticus.ro/static/img/sound.png)
### Camera
![Camera](http://iticus.ro/static/img/camera.png)
### Sensor
![Sensor](http://iticus.ro/static/img/sensor.png)