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

import socket, time, SocketServer
from threading import Thread


#config
BROADCAST_INTERVAL = 20         # Seconds between SSDP broadcast
BCAST_IP = "239.255.255.250"    # Broadcast to this IP Address
UPNP_PORT = 1900                # Port to respond to the SSDP requests
IP = "127.0.0.1"                # Bind to this IP Address
HTTP_PORT = 1901                # HTTP-port to serve icons and xml

FRIENDLY_NAME = "unknown_friendly_name"
SERIAL_NUMBER = "unknown_serial_number"
MAC_ADDRESS = "unknown_mac_address"
PROFILE_ID = "unknown_profile_id"
DEVICE_KEY = "unknown_device_key"
COMPONENTS = ""

M_SEARCH_REQ_MATCH = "M-SEARCH"

UPNP_BROADCAST = """NOTIFY * HTTP/1.1
HOST: 239.255.255.250:1900
CACHE-CONTROL: max-age=100
LOCATION: http://{}:{}/description.xml
SERVER: FreeRTOS/6.0.5, UPnP/1.0, IpBridge/0.1
NTS: ssdp:alive
NT: upnp:rootdevice
USN: uuid:{}::upnp:rootdevice

"""

UPNP_RESPOND = """HTTP/1.1 
CACHE-CONTROL: max-age=100
EXT:
LOCATION: http://{}:{}/description.xml
SERVER: FreeRTOS/6.0.5, UPnP/1.0, IpBridge/0.1
ST: urn:Muzzley:device:{}:1
USN: urn:Muzzley:device:{}:1

"""

DESCRIPTION_XML = """HTTP/1.1 200 OK
Content-type: text/xml
Connection: Keep-Alive

<?xml version="1.0"?>
<root>
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <URLBase>http://{}:{}/</URLBase>
    <device>
        <deviceType>urn:Muzzley:device:{}:1</deviceType>
        <friendlyName>{}</friendlyName>
        <manufacturer>Muzzley</manufacturer>
        <manufacturerURL>http://www.muzzley.com</manufacturerURL>
        <modelDescription>Muzzley Arduino Ciao Connector with UPnP Support</modelDescription>
        <modelName>Muzzley Arduino Ciao Connector</modelName>
        <modelNumber>0.0.1</modelNumber>
        <serialNumber>{}</serialNumber>
        <macAddress>{}</macAddress>
        <UDN>uuid:{}</UDN>
        <deviceKey>{}</deviceKey>
        <components>{}
        </components>
        <iconList>
            <icon>
                <mimetype>image/png</mimetype>
                <height>48</height>
                <width>48</width>
                <depth>24</depth>
                <url>muzzley_logo_0.png</url>
            </icon>
            <icon>
                <mimetype>image/png</mimetype>
                <height>120</height>
                <width>120</width>
                <depth>24</depth>
                <url>muzzley_logo_1.png</url>
            </icon>
        </iconList>
    </device>
</root>

"""

ICON_HEADERS = """HTTP/1.1 200 OK
Content-type: image/png

""".replace("\n", "\r\n")

ICON_SMALL = "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"
ICON_BIG = "iVBORw0KGgoAAAANSUhEUgAAAHgAAAB4CAMAAAAOusbgAAAC+lBMVEVMaXHXAgTYAgTXAgTYAgTXAgTYAgTYAgTXAgTYAgTYAgTYAgTYAgTYAgTYAgTXAgTXAgTXAgTXAgTXAgTXAgTYAgTXAgTXAgTYAgTXAgTYAgTXAgTXAgTXAgTXAgTYAgTXAgTYAgTYAgTXAgTXAgTXAgTYAgTXAgTXAgTYAgTXAgTXAgTXAgTYAgTXAgTXAgTXAgTYAgTYAgTYAgTYAgTXAgTYAgTXAgTYAgTXAgTXAgTYAgTXAgTXAgTXAgTYAgTXAgTYAgTYAgTXAgTYAgTXAgTXAgTYAgTXAgTXAQPYAgTXAAHYBQfZCw3ZCQvYBAXXAQLYAQPXAADXAALXAgTfMDHqdnfyqan1vr70urvwnJ3mYWLcHB3aEhTjSkzsgoPxo6PxpaXtiYrlVFXbGBreJijmXF3rfX7shYbpcnPiR0jbFhfXAgT74+T//v7////++vr3z8/kT1D1wMD99fb++fn3zM3mX2DdIyXuj5D64OD2xcbXAgTyra7//f398vLqenvZBwnpcHH87u7+/v7hOjzulJXvmZrmXV/qeHneKyz4z9D+/Pztjo799PT40tLcHyDdJCb41dX75eXgNTfwoKHaFBbnZ2jYAwTsh4j98fHzsLDXAgToaGn+///fMjT3ysraEBL0t7fWAgTXAgT2w8TaDhDeKSv++PjjTE3iREX87O376enfLjD2x8jlV1jXAgT63t70tbb63+D1u7zZDQ/519fXAgT86+zhOzzYAgTgNDbobG3iQkP86urhPT/YAgT52dnlWFrvlZb2yMnqdHbukpLzsrLcGhz87+/iRkfYAgTwnp/40tPdISP0ubrobW7jTk/tiovxp6j53N3gODreLS/nY2TrgIH75ubti4zoamv52dr1wcLshIX1u7vnZ2ncISLXAgTyqqv+9vbXAgTXAgTXAgTXAgTYAgThP0H41NTujo/gNzjXAgTYAgTXAgTXAgTXAgTYAgTYAgTXAgTXAgTXAgTYAgTXAgTXAgTXAgTYAgTXAgRViz12AAAA/nRSTlMAAw8oR2qLqMDS4+ru8u1pAhY8bZvF4PL7//8HJl+e1B2r4V0IkNkNT6+sU7j1RLEBl+/aZS34XFoUO8tM3VfmVun9L/krs/YL/z////////////+S//////////////////////////////8i////////////////////Yf////////////////////////////////////////+h////////Axj//////////////2////////8S///I//////+P/////////////9f/////////////////////////////E///onJBpWP/////QrQRSzP+upSTBGkFd8x3dolJAnwAAAueSURBVHgBvJaF1qtADIT/uruR1N3d3e39X+geDkvp7qVY5asMU5uSDYQ/nZjMFqvN7nC63B6vz+f3uF1Ohz1gtZiDf9/DFApHorF4ggNAEBC2uEQ8Fo2EQ6ZvpCZT6Uw2IWYhLzTgc2XSqeRnU4O5dL7AAQuSPwC88tlcwVHMfa7opXC5wolllQRQDq5SDpc+Elut1b0gD4oVF0VQb6NWfT+22WrDa1AIFCot2Xar+V50stNVjEUhUdKHbXc7xvusZ+kPEIW9IMpYJbx9i9EqB4akcUklkbWoTGVkqN7j/AQpgLWqTPJj/as7HQIiKKO6DlCZ6VzpuT2BgCg+SAZr1YPRZ5/ryU11OdAKongClbVcN6U9d7F87CKPKIzVynKh9ShareGjrFc9TbmbLXyY7U5Dcm+2x4+zn/XU93cPpG8FeR7ArNWRvFMLXhmqMwKgogX3SqWf10wrqx9Kj+sAZbtW7G3LEr/GUmFmzLugGWYsElGy3ZfnsKT9AF/kYH913i76pIFOlFpu1urFV5TPPQ7xy1SOsnM/T/W/FhCoSx51m6/KBAdO8HVOgf9zz0P8AcMzm5vsy09yHqKsNUSf7WzrAH7CwMp01gUFACilBgZtiTCfVbUXur92V/IhYCtOupffYq0hrtScMrfgGSSCzEusRSO0zE/BzavYOKAPalm02WtTyr3VNWXe7zLJkrCW/dA/Tq0C2I0ciU5qC5f578wx3zIXLfNqNUaFmTmWw8zMzInDyTJTmJmZmbmY4fTGbXkkU9W9D6pu/fJTS916PZnkxhc/1cSfveJVBOd+JBrjcdufSIpYLJ5MeDZEkouk7Qde+Uy3O9XdSojHatSsVbtO3Xr148zoA3iDho0aN2narHk8YRSFiLVo2ap1m7btBCtQyeq5Bqz9q5V4RbvWHVJSId2xpR9iZn6nzl3g79qtezTvV7w9evZKK3+X3t0jcfsQ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"

def set_IP(new_IP):
    global IP
    IP = new_IP
    
def read_IP():
    global IP
    return IP

def set_BROADCAST_INTERVAL(new_BROADCAST_INTERVAL):
    global BROADCAST_INTERVAL
    BROADCAST_INTERVAL = new_BROADCAST_INTERVAL
    
def read_BROADCAST_INTERVAL():
    global BROADCAST_INTERVAL
    return BROADCAST_INTERVAL

def set_BROADCAST_IP(new_BROADCAST_IP):
    global BCAST_IP
    BCAST_IP = new_BROADCAST_IP
    
def read_BROADCAST_IP():
    global BCAST_IP
    return BCAST_IP

def set_UPNP_PORT(new_UPNP_PORT):
    global UPNP_PORT
    UPNP_PORT = new_UPNP_PORT
    
def read_UPNP_PORT():
    global UPNP_PORT
    return UPNP_PORT

def set_HTTP_PORT(new_HTTP_PORT):
    global HTTP_PORT
    HTTP_PORT = new_HTTP_PORT
    
def read_HTTP_PORT():
    global HTTP_PORT
    return HTTP_PORT

def set_FRIENDLY_NAME(new_FRIENDLY_NAME):
    global FRIENDLY_NAME
    FRIENDLY_NAME = new_FRIENDLY_NAME
    
def read_FRIENDLY_NAME():
    global FRIENDLY_NAME
    return FRIENDLY_NAME

def set_SERIAL_NUMBER(new_SERIAL_NUMBER):
    global SERIAL_NUMBER
    SERIAL_NUMBER = new_SERIAL_NUMBER

def read_SERIAL_NUMBER():
    global SERIAL_NUMBER
    return SERIAL_NUMBER

def set_MAC_ADDRESS(new_MAC_ADDRESS):
    global MAC_ADDRESS
    MAC_ADDRESS = new_MAC_ADDRESS
    
def read_MAC_ADDRESS():
    global MAC_ADDRESS
    return MAC_ADDRESS

def set_PROFILE_ID(new_PROFILE_ID):
    global PROFILE_ID
    PROFILE_ID = new_PROFILE_ID
    
def read_PROFILE_ID():
    global PROFILE_ID
    return PROFILE_ID

def set_DEVICE_KEY(new_DEVICE_KEY):
    global DEVICE_KEY
    DEVICE_KEY = new_DEVICE_KEY
    
def read_DEVICE_KEY():
    global DEVICE_KEY
    return DEVICE_KEY

def set_DESCRIPTION_XML(new_DESCRIPTION_XML):
    global DESCRIPTION_XML
    DESCRIPTION_XML = new_DESCRIPTION_XML
    
def read_DESCRIPTION_XML():
    global DESCRIPTION_XML
    return DESCRIPTION_XML
    
def update_DESCRIPTION_XML():
    global DESCRIPTION_XML
    DESCRIPTION_XML = DESCRIPTION_XML.format(IP, HTTP_PORT, PROFILE_ID, FRIENDLY_NAME, SERIAL_NUMBER, MAC_ADDRESS, PROFILE_ID, DEVICE_KEY, COMPONENTS).replace("\n", "\r\n")

def set_UPNP_BROADCAST(new_UPNP_BROADCAST):
    global UPNP_BROADCAST
    UPNP_BROADCAST = new_UPNP_BROADCAST
    
def read_UPNP_BROADCAST():
    global UPNP_BROADCAST
    return UPNP_BROADCAST
    
def update_UPNP_BROADCAST():
    global UPNP_BROADCAST
    UPNP_BROADCAST = UPNP_BROADCAST.format(IP, HTTP_PORT, PROFILE_ID).replace("\n", "\r\n")

def set_UPNP_RESPOND(new_UPNP_RESPOND):
    global UPNP_RESPOND
    UPNP_RESPOND = new_UPNP_RESPOND
    
def read_UPNP_RESPOND():
    global UPNP_RESPOND
    return UPNP_RESPOND
    
def update_UPNP_RESPOND():
    global UPNP_RESPOND
    UPNP_RESPOND = UPNP_RESPOND.format(IP, HTTP_PORT, PROFILE_ID, PROFILE_ID).replace("\n", "\r\n")

def set_ICON_HEADERS(new_ICON_HEADERS):
    global ICON_HEADERS
    ICON_HEADERS = new_ICON_HEADERS.replace("\n", "\r\n")
    
def read_ICON_HEADERS():
    global ICON_HEADERS
    return ICON_HEADERS
    
def set_ICON_SMALL(new_ICON_SMALL):
    global ICON_SMALL
    ICON_SMALL = new_ICON_SMALL
 
def read_ICON_SMALL():
    global ICON_SMALL
    return ICON_SMALL

def set_ICON_BIG(new_ICON_BIG):
    global ICON_BIG
    ICON_BIG = new_ICON_BIG
 
def read_ICON_BIG():
    global ICON_BIG
    return ICON_BIG

def set_COMPONENTS(new_COMPONENTS):
    global COMPONENTS
    COMPONENTS = ""
    for component in new_COMPONENTS:
        COMPONENTS = COMPONENTS + \
                    "\n            <component>\n" + \
                    "                <id>" + component["id"] + "</id>\n" + \
                    "                <label>" + component["label"] + "</label>\n" + \
                    "                <type>" + component["type"] + "</type>\n" + \
                    "            </component>"

def read_COMPONENTS():
    global COMPONENTS
    return COMPONENTS


class Broadcaster(Thread):
    interrupted = False
    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20)
        
        while True:
            sock.sendto(UPNP_BROADCAST, (BCAST_IP, UPNP_PORT))
            for x in range(BROADCAST_INTERVAL):
                time.sleep(1)
                if self.interrupted:
                    sock.close()
                    return

    def stop(self):
        self.interrupted = True
 
class Responder(Thread):
    interrupted = False
    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('', UPNP_PORT))
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(BCAST_IP) + socket.inet_aton(IP));
        sock.settimeout(1)

        while True:
            try:
                data, addr = sock.recvfrom(1024)
            except socket.error, msg:
                if self.interrupted:
                    sock.close()
                    return
            else:
                if M_SEARCH_REQ_MATCH in data:
                    #print "received M-SEARCH from ", addr, "\n", data
                    self.respond(addr)
        

    def stop(self):
        self.interrupted = True

    def respond(self, addr):
        outSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        outSock.sendto(UPNP_RESPOND, addr)
        outSock.close()
        #print "Response sent to:", addr, "\n", UPNP_RESPOND

class Httpd(Thread):
    def run(self):
        SocketServer.ThreadingTCPServer.allow_reuse_address = True
        self.server = SocketServer.ThreadingTCPServer((IP, HTTP_PORT), HttpdRequestHandler)
        self.server.serve_forever() 
    def stop(self):
        self.server.socket.close()
        self.server.server_close()

class HttpdRequestHandler(SocketServer.BaseRequestHandler ):
    def handle(self):
        data = self.request.recv(1024)
        if "description.xml" in data:
            self.request.sendall(DESCRIPTION_XML)
        elif "muzzley_logo_0.png" in data:
            self.request.sendall(ICON_HEADERS)
            self.request.sendall(ICON_SMALL.decode('base64'))
        elif "muzzley_logo_1.png" in data:
            self.request.sendall(ICON_HEADERS)
            self.request.sendall(ICON_BIG.decode('base64'))
        else:
            self.request.sendall("HTTP/1.1 404 Not Found")
