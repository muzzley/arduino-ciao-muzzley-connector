# Arduino Ciao Muzzley Connector #

This repo contains the code for the Arduino Ciao - Muzzley client connector library.


# What is Arduino Ciao?

Ciao Connectors makes the Arduino boards able to communicate with the "outside world" very easily.

It only needs the Ciao Library running on the MCU (microcontroller) side to interact with your Arduino sketch code, and the Ciao Core running over the Linino OS to enable the communication with several modules called connectors.

More info about Arduino Ciao: [http://labs.arduino.org/ciao](http://labs.arduino.org/ciao)


# How do I get set up?

##Dependencies

* [Linino OS](http://www.linino.org) running on a Arduino / Linino compatible board. More info about the Linino OS installation on a Arduino Yun board can be found [here](http://labs.arduino.org/How+to+upgrade+the+Linino+distribution+for+Arduino+Yun)
* Install Arduino Ciao Core following the instructions [here](http://labs.arduino.org/Ciao+setup)
* Install the Arduino [Ciao Library](https://github.com/arduino-org/CiaoMCU) on the [Arduino IDE](https://www.arduino.cc/en/Main/Software) / [Arduino Studio](http://labs.arduino.org/tiki-index.php?page=Arduino+Studio)
* Install the following python module dependencies on the Linino OS:
    * distribute
    * python-openssl
    * pip
    * requests

##Install the Muzzley connector

###If the board already has the Ciao core installed, just add the Muzzley connector:

1) Copy the Muzzley Connector folder to the Arduino Ciao **connectors** folder

2) Copy the Muzzley Connector configuration file to the Arduino Ciao **conf** folder

###If it doesn´t, the ciao core must be also installed in first place:

1) Get the Ciao core from [here](https://github.com/arduino-org/Ciao) and install it on the **/usr/lib/python2.7/** folder.

2) Add the missing **run-ciao** bash script on the **/usr/bin** folder with the following content:

```
cd /usr/lib/python2.7/ciao
exec python -u ciao.py 2> /var/log/run-ciao.log
´´´

For more details check the [official Arduino Ciao webpage](http://labs.arduino.org/Ciao).

##Create your Muzzley App

1) Login on our [developers website](https://www.muzzley.com/developers) (or create a new account) and open the Apps page.

2) Now click on Create App and give your Muzzley App a name and a description like "Arduino Yun" and "Arduino Yun Muzzley example".

3) Select the Integration Type as "Cloud to Device" and add a name to the Provider field like "Arduino". It reffers to the manufacturers name that is integrating their products with us.

4) Complete the folowing fields "Profile Photo URL", "Channel Photo URL" and "Tile Photo URL" with some product images URLs. This images will appear on the Muzzley app then the user will add a new device, and on the respectve devices list.

5) The "Interface UUID" refers to the Muzzley interface that will be presented to the end user. You can update this field later, after reading our Interface documentation [here](http://clients.muzzley.com/documentation#interfaces), and implemeting you own interface. For now, please continue with the following steps to create your Muzzley App.

6) Select the "Device discovery" as "UPNP". This is the method used by the Arduino Ciao Muzzley connector to authenticate the device in your local network. 

7) Finally add some e-mail addresses to the "Email Access List", including yours. This is the list of authortized users to add your Arduino devices using your Arduino Muzzley App.

8) Click on "save changes" to store your configuration.

9) Now you will have to create a "profile spec" to specify some characterictics of your product. Please read our documentation on the following [link](http://clients.muzzley.com/documentation#selfcare).


##Update your connector configuration file


1) Update the Muzzley connector configuration file muzzley.json.conf in the **/etc/muzzley/** folder with the details about your own Muzzley App.

* **app_uuid** - Muzzley App unique identifier.

* **app_token** - Muzzley App authentincation token.

* **profile_id** - Muzzley profile specification unique identifier.

* **serial_number** - It can be any uuid string referring one instace of your device.
                      For exampe if your have 2 boards running your Muzzley App, they must be identified with different uuid's.

* **friendly_name** - It will be the custom name of your device.
                      It may be changed as as you will at any time, and it will be presented to the user on the Muzzley App as the primary device name.

* **components** -  One array with the Arduino componets acordingly with what as specicfied on our website. Id must contain the id, label and type for each one of them.


Example of a complete configuration file:

```json
{
    "name": "muzzley",
    "description": "Muzzley (v0.0.1) connector for Ciao Core",
    "version": "0.0.1",
    "ciao": {
        "host": "127.0.0.1",
        "port": 8900
    },
    "params": {
        "app_uuid": "<your-muzzley-app-uuid>",
        "profile_id": "<your-muzzley-app-profile_id>",
        "app_token": "<your-muzzley-app-app_token>",
        "serial_number": "<your-arduino-random-uuid>",
        "friendly_name": "My Arduino Yun",
        "components": [
            {
                "id": "yunlock1",
                "label": "Arduino Lock",
                "type": "lock"
            },
            {
                "id": "temp-sensor1",
                "label": "Temperature Sensor",
                "type": "temp-sensor"
            }
        ]
    }
}
```

##Check the connector log file

1) The connector log entries are being stored on the file: **/var/log/muzzley.log**


##Write your Arduino sketch using the Ciao Library 


1) Include the Arduino Ciao Library and start it on the Setup()

```c++
#include <Ciao.h>

void setup() {
  Ciao.begin(115000);
}
```

2)Read a Message from the Muzzley cloud

```c++
void loop() {
  CiaoData data;
  data = Ciao.read("muzzley");

  String command[4];
  String io;
  String component;
  String property;
  String value;
  
  if(!data.isEmpty()){
    
    String id = data.get(0);
    String message = data.get(1);

    Serial.print("\nMessage Id: ");  // Ciao message ID
    Serial.print(id); 
    Serial.print("\nMessage: ");     // Muzzley Message (io/Component/Property/Value)
    Serial.print(message);
  
    splitString(message, "|", command, 4);
    
    io = command[0];
    component = command[1];
    property = command[2];
    value = command[3];

  }
    
  delay(500);
}

```

3) Parse the value object

```c++
void parseValue(String value) {
  //String with the Value object received from the Muzzley cloud acoordingly with the profile spec
  //The r, g and b represents the keys of the object and the numbers, the respective intensities of a RGB color object
  String value = String("r_1_g_2_b_3"); 

  //Size of the Value object
  int size = 6;

  splitString(value, "_", command, size);

  String r_key = command[0];
  String r_value = command[1];
  String g_key = command[2];
  String g_value = command[3];
  String b_key = command[4];
  String b_value = command[5];

  int r = r_value.toInt();
  int g = g_value.toInt();
  int b = b_value.toInt();
}

```

4) Write a Message to the Muzzley cloud

```c++
void sendMessage(String message) {
  //Send a message to the Muzzley cloud
  //The message is a string with the following format: "Component_id|Property_id|ValueObject"
  Ciao.write("muzzley", message);

  //For example:
  Ciao.write("muzzley", "plug1/status/true");				//For a Boolean value
  Ciao.write("muzzley", "temp_sensor1/temperature/23");		//For an Integer 
  Ciao.write("muzzley", "bulb2/brightness/0.13");			//For a Float
  Ciao.write("muzzley", "bulb2/color/r_1_g_2_b_3");			//For an Object
}

```

5) Write a Message Response to the Muzzley cloud


```c++
void sendMessageResponse(String id, String message) {
  //Send a message response to the Muzzley cloud
  //The message is a string with the following format: "Component_id|Property_id|ValueObject"
  //The Ciao Message id from the original request must be provided, to correlate this answer with the original request.
  Ciao.write("muzzley", id, message);

  //For example:
  Ciao.write("muzzley", id, "plug1/status/true");				//For a Boolean value
  Ciao.write("muzzley", id, "temp_sensor1/temperature/23");		//For an Integer 
  Ciao.write("muzzley", id, "bulb2/brightness/0.13");			//For a Float
  Ciao.write("muzzley", id, "bulb2/color/r_1_g_2_b_3");			//For an Object
}

```