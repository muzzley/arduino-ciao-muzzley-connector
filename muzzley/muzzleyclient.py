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

from Queue import Queue
import paho.mqtt.client as mqtt
import requests
import logging
import json
import ssl
import time

import muzzleyupnp


class MuzzleyClient():

	subscribed_topics = []

	responder = muzzleyupnp.Responder()
	broadcaster = muzzleyupnp.Broadcaster()
	httpd = muzzleyupnp.Httpd()

	def __init__(self, muzzley_params, ciao_queue):
		
		self.logger = logging.getLogger("muzzley.client")
		
		#validate params - START
		missing_params = []
		required_params = ["host", "port", "globalmanager_host", "ip_address", "device_key_filepath", "app_uuid", "profile_id", "app_token", "serial_number", "mac_address", "friendly_name", "components"]
		for p in required_params:
			if not p in muzzley_params:
				missing_params.append(p)

		if len(missing_params) > 0:
			raise RuntimeError("Muzzley configuration error, missing: %s" % ",".join(missing_params))

		if not "qos" in muzzley_params:
			muzzley_params["qos"] = 0
			
		#validate params - END	
		
		#Read the stored device key from file
		try:
			devicekeyfile = open(muzzley_params["device_key_filepath"], "r")
			muzzley_params["device_key"] = devicekeyfile.read()
			devicekeyfile.close()
			self.logger.info("Read the the stored device_key sucessfully")
		except Exception, e:
			self.logger.info("Could not read the stored device_key")
			muzzley_params["device_key"] = ""


		#Muzzley Global-Manager authentication
		register_headers = {'Content-type': 'application/json', 'Accept': '*/*', 'Host': muzzley_params["globalmanager_host"]}
		register_url = "http://" + muzzley_params["globalmanager_host"] + "/deviceapp/register"
		
		if "device_key" in muzzley_params:
			if muzzley_params["device_key"] != "":
				register_body = {
					"profileId": muzzley_params["profile_id"],
					"macAddress": muzzley_params["mac_address"],
					"serialNumber": muzzley_params["serial_number"],
					"friendlyName": muzzley_params["friendly_name"],
					"deviceKey":  muzzley_params["device_key"]
				}
			else:
				register_body = {
				"profileId": muzzley_params["profile_id"],
				"macAddress": muzzley_params["mac_address"],
				"serialNumber": muzzley_params["serial_number"],
				"friendlyName": muzzley_params["friendly_name"]
			}
		else:
			register_body = {
				"profileId": muzzley_params["profile_id"],
				"macAddress": muzzley_params["mac_address"],
				"serialNumber": muzzley_params["serial_number"],
				"friendlyName": muzzley_params["friendly_name"]
			}
			
		r = requests.post(register_url, data=json.dumps(register_body), headers=register_headers)
		
		if r.status_code is 200 or r.status_code is 201:
			if r.status_code is 200:
				self.logger.debug("The provided deviceKey for this device was accepted")
			elif r.status_code is 201:
				self.logger.debug("Muzzley created a new deviceKey for this device")
		
			response = json.loads(r.text)
			deviceKey = response["deviceKey"]
			components_url = response["urls"]["components"]
			self.logger.debug("Current deviceKey: %s" % deviceKey)
			
			components_headers = {'Content-type': 'application/json', 'Accept': '*/*', 'Host': muzzley_params["globalmanager_host"], 'serialNumber': muzzley_params["serial_number"], 'deviceKey': deviceKey}
			components_body = {
				"components": muzzley_params["components"]
			}
			
			r = requests.post(components_url, data=json.dumps(components_body), headers=components_headers)
			
			if r.status_code is 200:
				self.logger.debug("The Muzzley components list was updated successfully")
			else:
				self.logger.debug("Something went wrong when updating the compoenents list...")
				self.logger.debug(r.text)
			
		else:
			self.logger.debug("Something went wrong when registering this device...")
			self.logger.debug(r.text)
		
		#stores the deviceKey in muzzley params dictionary
		muzzley_params["device_key"] = deviceKey
		
		#Stores the device key on file
		try:
			devicekeyfile = open(muzzley_params["device_key_filepath"], "w")
			devicekeyfile.write(muzzley_params["device_key"])
			devicekeyfile.close()
			self.logger.info("Stored device key sucessfully on file")
		except Exception, e:
			self.logger.info("Could not store the device key on file")
		

		#Configuring the Muzzley UPNP Advertiser
		muzzleyupnp.set_IP(muzzley_params["ip_address"])
		muzzleyupnp.set_PROFILE_ID(muzzley_params["profile_id"])
		muzzleyupnp.set_FRIENDLY_NAME(muzzley_params["friendly_name"])
		muzzleyupnp.set_MAC_ADDRESS(muzzley_params["mac_address"])
		muzzleyupnp.set_SERIAL_NUMBER(muzzley_params["serial_number"])
		muzzleyupnp.set_DEVICE_KEY(muzzley_params["device_key"])
		muzzleyupnp.set_COMPONENTS(muzzley_params["components"])

		muzzleyupnp.update_UPNP_BROADCAST()
		muzzleyupnp.update_UPNP_RESPOND()
		muzzleyupnp.update_DESCRIPTION_XML()

		#self.logger.debug(muzzleyupnp.read_IP())
		#self.logger.debug(muzzleyupnp.read_HTTP_PORT())
		#self.logger.debug(muzzleyupnp.read_BROADCAST_IP())
		#self.logger.debug(muzzleyupnp.read_UPNP_PORT())
		#self.logger.debug(muzzleyupnp.read_COMPONENTS())
		#self.logger.debug(muzzleyupnp.read_UPNP_BROADCAST())
		#self.logger.debug(muzzleyupnp.read_UPNP_RESPOND())
		#self.logger.debug(muzzleyupnp.read_DESCRIPTION_XML())

		#reference to Queue for exchanging data with CiaoCore
		self.ciao_queue = ciao_queue

		#local instance of MQTT Client
		self.handle = mqtt.Client(muzzley_params["friendly_name"], True)
		self.handle.on_connect = self.on_connect
		self.handle.on_message = self.on_message

		if "ssl_cert" in muzzley_params:
			self.handle.tls_set(muzzley_params["ssl_cert"], certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1, ciphers=None)
			self.logger.debug("Using the following ssl cerificate: %s" % muzzley_params["ssl_cert"])


		version = "v1"
		namespace = "iot"
		self.topic_delimiter = "/"
		manager_topic = version + self.topic_delimiter + namespace + self.topic_delimiter + "profiles" + \
						self.topic_delimiter + muzzley_params["profile_id"] + self.topic_delimiter + "channels" + \
						self.topic_delimiter + muzzley_params["device_key"] + self.topic_delimiter + "#"

		#For debug purposes it can subscribe all messages from the same profile id
		#manager_topic = version + self.topic_delimiter + namespace + self.topic_delimiter + "profiles" + \
		#				self.topic_delimiter + muzzley_params["profile_id"] + self.topic_delimiter + "#"
		
		self.logger.debug("Set Muzzley topic to: %s" % manager_topic)

		self.subscribed_topics = [manager_topic]
		self.client_id = muzzley_params["friendly_name"]
		self.host = muzzley_params["host"]
		self.port = muzzley_params["port"]
		self.qos = muzzley_params["qos"]

		#SET authentication params (retrieved from configuration file under muzzley/muzzley.json.conf)
		if muzzley_params["app_uuid"] and muzzley_params["app_token"]:
			self.handle.username_pw_set(str(muzzley_params["app_uuid"]), str(muzzley_params["app_token"]))
			self.logger.debug("Set the app_uuid to: %s and app_token to: %s" % (str(muzzley_params["app_uuid"]), str(muzzley_params["app_token"])))

		#Start UPNP Advertiser
		self.httpd.start()
		self.responder.start()
		self.broadcaster.start()
		self.httpd.join(1)
		self.responder.join(1)
		self.broadcaster.join(1)

	def on_connect(self, client, userdata, flags, rc):
		self.logger.info("Connected to Muzzley MQTT broker with result code %s" % str(rc))

		for topic in self.subscribed_topics:
			if topic: #prevent issues from specifying empty topic
				self.logger.debug("Subscribing to the Muzzley topic: %s" % topic)
				self.handle.subscribe(str(topic), qos=self.qos)

	def on_message(self, client, userdata, msg):
		self.logger.debug("Got new message. Topic: %s Message: %s" % (str(msg.topic), str(msg.payload)))
		#print "Topic: %s" % msg.topic
		#print "Payload: %s" % msg.payload

		parsed_topic = msg.topic.split(self.topic_delimiter)

		##------- parse topic --------##
		version = parsed_topic[0]
		namespace = parsed_topic[1]
		profileid = parsed_topic[3]
		channelid = parsed_topic[5]
		componentid = parsed_topic[7]
		propertyid = parsed_topic[9]


		##------- parse message -------##
		lvalue = []
		self.logger.debug("Parsed message:")
		payload = json.loads(str(msg.payload))
		io = payload["io"]
		if "data" in payload:
			data = payload["data"]
			if "value" in data:
				value = data["value"]
				if value is None:
					self.logger.debug("Value: null")
					lvalue.append("null")
				else:
					if type(value) is bool:
						self.logger.debug("Value: %s" % value)
						lvalue.append(str(value))
					elif type(value) is int:
						self.logger.debug("Value: %s" % value)
						lvalue.append(str(value))
					elif type(value) is float:
						self.logger.debug("Value: %s" % value)
						lvalue.append(str(value))
					elif type(value) is str:
						self.logger.debug("Value: %s" % value)
						lvalue.append(str(value))
					elif type(value) is dict:
						for key in value:
							self.logger.debug("Value of key: %s is: %s" % (str(key), str(value[key])))
							lvalue.append(str(key))
							lvalue.append(str(value[key]))

		if len(lvalue) == 0:
			lvalue.append("null")

		if "u" in payload:
			muzzley_user = payload["u"]
			muzzley_userid = muzzley_user["id"]
			muzzley_username = muzzley_user["name"]
			self.logger.debug("Muzzley Userid: %s" % muzzley_userid)
			self.logger.debug("Muzzley UserName: %s" %muzzley_username)

		if "_cid" in payload:
			cid = payload["_cid"]
			self.logger.debug("_cid: %s" % str(cid))
		else:
			cid = "null"

		self.logger.debug("Version: %s" %version)
		self.logger.debug("Namespace: %s" %namespace)
		self.logger.debug("Profileid: %s" %profileid)
		self.logger.debug("Componentid: %s" % componentid)
		self.logger.debug("Propertyid: %s" % propertyid)
		self.logger.debug("IO: %s" % io)

		value_delimiter = "_"
		value_payload = value_delimiter.join(lvalue)
		lmcu = [str(io), str(componentid), str(propertyid)]
		lmcu.append(value_payload)

		#Building the message to send to the MCU
		mcu_delimiter = "|"
		mcu_payload = mcu_delimiter.join(lmcu)
		self.logger.debug("Message sent to the MCU: %s" % mcu_payload)

		#Building the user info to send to the MCU
		#luser = [str(muzzley_userid), str(muzzley_username)]
		#mcu_user = mcu_delimiter.join(luser)
		#self.logger.debug("Muzzley user info sent to the MCU: %s" % mcu_user)

		entry = {
			"data" : [str(mcu_payload), str(cid)]
			#"data" : [str(mcu_payload), str(cid), str(mcu_user)]
		}

		self.ciao_queue.put(entry)
		time.sleep(0.2)

	def connect(self):
	    while True:
			try:
				if self.handle.connect(self.host, self.port, 60) == 0:
					self.handle.loop_start()
					return True
			except:
				pass

	def disconnect(self):
		self.httpd.stop()
		self.responder.stop()
		self.broadcaster.stop()

		self.handle.loop_stop()
		self.handle.disconnect()

	def publish(self, topic, message, qos=None):
		if not qos:
			qos = self.qos
		self.logger.debug("Publishing message. Topic: %s Message: %s" % (topic, str(message)))
		self.handle.publish(topic, str(message), qos)
