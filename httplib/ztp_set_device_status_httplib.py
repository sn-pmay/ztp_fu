#!/usr/bin/python

import sys
import os
import json
import argparse
import subprocess
import logging
import time
import httplib
import socket
from httplib import HTTPConnection

# Defaults
hostname = 'localhost'
port = '8080'

httpSuccessCodes = [200, 201, 202, 204]
method = 'PUT'
statuses = [
	'START', 'DONE', 'CONFIG', 'AWAIT-ONLINE', 'AWAIT-SYSTEM-READY', 'OS-INSTALL', 'OS-REBOOTING', 'FAILED'
]

parser = argparse.ArgumentParser()
parser.add_argument('status', help='AEON ZTP status. Valid options are: {}'.format(statuses))
parser.add_argument('--dry-run', help="Does input validation, prints what would be done, but doesn't actually do anything.", action='store_true')
parser.add_argument('--ztp_host', help='Remote host against which to run. Default: {}'.format(hostname))
parser.add_argument('--ztp_port', help='Remote host port against which to run. Default: {}'.format(port))
parser.add_argument('--ssl', help='Should the connection be treated as an SSL/TLS protected connection', action='store_true')
arser.add_argument('--device_ip', help='The device IP for which to set the status', required=True)
parser.add_argument('--device_os', help='The device OS', required=True)
parser.add_argument('--verbose', help='Make things chatty. Note: May display sensitive data like password', action='store_true')

args = parser.parse_args()
if args.verbose:
  print "****** Verbose mode ****"
  for arg in vars(args):
     print "Argument: {}".format(arg)
     print "|-> Value: {}".format(getattr(args, arg))

status = args.status
if status.upper() not in statuses:
  print "ERROR: {} is not a valid ZTP status.".format(status)
  print "Valid statuses are: {}".format(statuses)
  exit(1)

if args.ztp_host:
  hostname = '{}'.format(args.ztp_host)
if args.ztp_port:
  port = '{}'.format(args.ztp_port)
if args.ssl:
  protocol="https"
else:
  protocol="http"

URL_BASE = '{}:{}'.format(hostname, port)
URL = '/api/devices/status'
url_headers = {'Content-Type': 'application/json', 'Accept': 'application/json' }
request_url="{}://{}{}".format(protocol, URL_BASE, URL)
if args.verbose: print "Request_url: \"{}\"".format(request_url)

# device_data = dict(
#   ip_addr = args.device_ip,
#   serial_number="EC1713003123",
#   hw_model="accton_as4610_54",
#   os_version="2.0.0-2017-07-19.1529-40fc82b_armel",
#   os_name="ONL",
#   state = args.status
# )

# The device is found via the IP and OS tupple.
# An update of status if the OS string has changed will fail.
device_data = dict(
  ip_addr = args.device_ip,
  os_name = args.device_os,
  state   = args.status
)

# print device_data
json_string = json.dumps(device_data)
# print json_string

if args.dry_run:
  print "DRY-RUN: {} {} JSON:'{}'".format(request_url, method, json_string)
  exit(0)



try:
  conn = httplib.HTTPConnection(URL_BASE)
  if args.verbose: 
    logging.basicConfig(level=logging.DEBUG)
    conn.set_debuglevel(11)
    HTTPConnection.debuglevel = 1
  conn.request(method, URL, json_string, url_headers)
  r1 = conn.getresponse()
  if args.verbose:
    print "Response: {}, reason: {}".format(r1.status, r1.reason)
  if r1.status in httpSuccessCodes:
    data = r1.read()
    ztp_status = json.loads(data)['ok']
    if not ztp_status:
      print "ZTP status returned an error:"
      print json.dumps(json.loads(data), sort_keys=True, indent=4)
  else:
    print "Response: {}, reason: {}".format(r1.status, r1.reason)
    print "Non-200 HTTP response seen. Something went awry."
    data = r1.read()
    print json.dumps(json.loads(data), sort_keys=True, indent=4)
except ValueError as e:
  print "Got the following data back: {}".format(data)
  print "JSON parse error: {}".format(e)
  exit(1)
except socket.error as e:
  print "ERROR: Socket Error"
  print "Tried to access 'http://{}'".format(URL_BASE)
  print "ERROR: {}".format(e)
  exit(1)