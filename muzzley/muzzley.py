#!/usr/bin/python
###
#
# This file is part of Arduino Ciao
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright 2015 Arduino Srl (http://www.arduino.org/)
# Copyright 2015 Muzzley (http://www.muzzley.com/)
#
# authors:
# jorge.claro@muzzley.com
#
###

import os, sys, signal
import json, logging
from Queue import Queue
import time

from muzzleyciao import MuzzleyCiao
from muzzleyclient import MuzzleyClient
import paho.mqtt.client as mqtt

import socket  #IP  ADDRESS
import fcntl   #MAC ADDRESS
import struct  #MAC ADDRESS


def getHwAddr(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', ifname[:15]))
    s.close()
    return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]


def getIpAddr():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("muzzley.com", 80))
    IP = s.getsockname()[0]
    s.close()
    return IP

# function to handle SIGHUP/SIGTERM
def signal_handler(signum, frame):
	global logger
	logger.info("SIGNAL CATCHED %d" % signum)
	global shd
	shd["loop"] = False

#shared dictionary
shd = {}
shd["loop"] = True
shd["basepath"] = os.path.dirname(os.path.abspath(__file__)) + os.sep
shd["configpath"] = "/etc/muzzley/"
shd["logpath"] = "/var/log/"

#init log
logging.basicConfig(filename=shd["logpath"]+"muzzley.log", level=logging.DEBUG)
logger = logging.getLogger("muzzley")


#read configuration
# TODO: verify configuration is a valid JSON
if os.path.exists(shd["configpath"]+"muzzley.json.conf"):
	json_conf = open(shd["configpath"]+"muzzley.json.conf").read()
	shd["conf"] = json.loads(json_conf)
else:
	logger.critical("Muzzley configuration file does not exist")
	sys.exit(1)

#get the Muzzley core and global manager endpoints from cmd line arguments
muzzley_mqtt_host = sys.argv[1]
muzzley_mqtt_port = sys.argv[2]
muzzley_globalmanager_host = sys.argv[3]
muzzley_interface = sys.argv[4]
if len(sys.argv) >= 6:
	shd["conf"]["params"]["ssl_cert"] = "/etc/ssl/certs/" + sys.argv[5]

shd["conf"]["params"]["host"] = muzzley_mqtt_host
shd["conf"]["params"]["port"] = muzzley_mqtt_port
shd["conf"]["params"]["globalmanager_host"] = muzzley_globalmanager_host
shd["conf"]["params"]["mac_address"] = getHwAddr(str(muzzley_interface))
shd["conf"]["params"]["ip_address"] = getIpAddr()
shd["conf"]["params"]["device_key_filepath"] = shd["configpath"] + "devicekey.key"


#forking to make process standalone
try:
	pid = os.fork()
	if pid > 0:
		# Save child PID to file and exit parent process
		runfile = open("/var/run/muzzley-ciao.pid", "w")
		runfile.write("%d" % pid)
		runfile.close()
		sys.exit(0)

except OSError, e:
	logger.critical("Fork failed")
	sys.exit(1)

muzzley_queue = Queue()
ciao_queue = Queue()

try:
	muzzleyclient = MuzzleyClient(shd["conf"]["params"], ciao_queue)
	
except Exception, e:
	logger.critical("Exception while creating MuzzleyClient: %s" % e)
	sys.exit(1)

signal.signal(signal.SIGINT, signal.SIG_IGN) #ignore SIGINT(ctrl+c)
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if muzzleyclient.connect():
	logger.info("Connected to Muzzley MQTT broker: %s" % shd['conf']['params']['host'])
	
	shd["requests"] = {}

	ciaoclient = MuzzleyCiao(shd, muzzley_queue, ciao_queue)
	ciaoclient.start()

	# endless loop until SIGHUP/SIGTERM
	while shd["loop"]:
		
		#if received a entry message from MCU
		if not muzzley_queue.empty():
			entry = muzzley_queue.get()
			logger.debug("Received Entry from MCU: %s" % entry)
			
			# if entry received from ciao is a "response"
			if entry['type'] == "response":
				original_checksum = entry["source_checksum"]
				#logger.debug("Original checksum from the response message: %s" % original_checksum)
				if not original_checksum in shd["requests"]:
					logger.warning("Received response to unknown checksum %s" % original_checksum)
					continue
				original_message = shd["requests"][original_checksum]
				cid = str(original_message['data'][1])
				#user = str(original_message['data'][2])
				
			message = str(entry['data'][0])

			#message from mcu : component/property/value
			mcu_delimiter = '|'
			msg_list = message.split(mcu_delimiter)
			
			componentid = msg_list[0]
			propertyid = msg_list[1]
			mcu_value = msg_list[2]
	
			logger.debug("Received from mcu:")
			logger.debug("Componentid: %r" % componentid)
			logger.debug("Propertyid: %r" % propertyid)
			logger.debug("MCU response value %r" % mcu_value)
				
			mcu_value_delimiter = '_'
			value_list = mcu_value.split(mcu_value_delimiter)
			logger.debug("MCU response value list %r" % value_list)
				
				
			value_dict = dict(zip(value_list[::2], value_list[1::2]))
			for key in value_dict:
				logger.debug("MCU respone value for key: %s is: %r" % (str(key), value_dict[key]))
				
			logger.debug("MCU response value dict: %r" % value_dict)
					
			version = "v1"
			namespace = "iot"
			profileid = shd["conf"]["params"]["profile_id"]
			channelid = shd["conf"]["params"]["device_key"]

			#topic to muzzley: version/namespace/channels/channel_id/components/component_id/properies/property_id
			topic_delimiter = "/"
			topic_list = [str(version), str(namespace), "profiles", str(profileid), "channels", str(channelid), "components", str(componentid), "properties", str(propertyid)]
			muzzley_topic = topic_delimiter.join(topic_list)
					
			if len(value_dict) > 0:
				value_str = value_dict
			else:
				if mcu_value == "True" or mcu_value == "true":
					value_str = True
				elif mcu_value == "False" or mcu_value == "false":
					value_str = False
				else:
					value_str = mcu_value
			
			io = "i"
			success = True
			error_message = ""
			
			#message to muzzley: io/success/message/data/_cid
			if entry['type'] == "response":
				if success is True:
					muzzley_message = {
						"success": success,
						"io": io,
						"data": {
							"value": value_str
						},
						"_cid": cid
					}
				else:
					muzzley_message = {
						"success": success,
						"message": error_message,
						"io": io,
						"data": {
							"value": value_str
						},
						"_cid": cid
					}
			else:
				muzzley_message = {
					"io": io,
					"data": {
						"value": value_str
					}
				}
				
			logger.debug("Muzzley topic")
			logger.debug(muzzley_topic)
			
			logger.debug("Muzzley message:")
			logger.debug(json.dumps(muzzley_message))
								
			
			#publishes the entry message to the Muzzley Core
			muzzleyclient.publish(muzzley_topic, json.dumps(muzzley_message))

		# the sleep is really useful to prevent ciao to cap all CPU
		# this could be increased/decreased (keep an eye on CPU usage)
		# time.sleep is MANDATORY to make signal handlers work (they are synchronous in python)
		time.sleep(0.01)
		
	muzzleyclient.disconnect()
	logger.info("Muzzley connector is closing")
	sys.exit(0)

else:
	logger.critical("Unable to connect to %s" % shd["conf"]["params"]["host"])