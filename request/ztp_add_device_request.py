#!/usr/bin/python
import sys
import os
import json
import argparse
import subprocess
import logging
import time
import requests
import socket
from httplib import HTTPConnection
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Defaults
hostname = 'localhost'
port = '8080'

httpSuccessCodes = [200, 201, 202, 204]

parser = argparse.ArgumentParser()
parser.add_argument('--dry-run', help="Does input validation, prints what would be done, but doesn't actually do anything.", action='store_true')
parser.add_argument('--host', help='Remote host against which to run. Default: localhost')
parser.add_argument('--port', help='Remote host port against which to run. Default: 8080')
parser.add_argument('--ssl', help='Should the connection be treated as an SSL/TLS protected connection', action='store_true')
parser.add_argument('--user', help='Basic AUTH username')
parser.add_argument('--verbose', help='Make things chatty. Implies --curl. Note: May display sensitive data like password', action='store_true')

args = parser.parse_args()
if args.verbose:
  print "****** Verbose mode ****"
  for arg in vars(args):
     print "Argument: {}".format(arg)
     print "|-> Value: {}".format(getattr(args, arg))

if args.host:
  hostname = '{}'.format(args.host)
if args.port:
  port = '{}'.format(args.port)
if args.ssl:
  protocol="https"
else:
  protocol="http"

URL_BASE = '{}:{}'.format(hostname, port)
URL = '/api/devices'
url_headers = {'Content-Type': 'application/json', 'Accept': 'application/json' }
request_url="{}://{}{}".format(protocol, URL_BASE, URL)
if args.verbose: print "Request_url: \"{}\"".format(request_url)

if args.dry_run:
  print "DRY-RUN: {} {} JSON:'{}'".format(request_url, method, blob)
  exit(0)

device_data = dict(
  ip_addr="172.31.0.50",
  serial_number="EC1713003123",
  hw_model="accton_as4610_54",
  os_version="2.0.0-2017-07-19.1529-40fc82b_armel",
  os_name="ONL",
  message="Intial device add"
)
# print device_data

try:
  # verify set to False because we are not ready to do SSL cert verification
  if args.verbose: 
    logging.basicConfig(level=logging.DEBUG)
    HTTPConnection.debuglevel = 1
  conn = requests.post(url=request_url, json=device_data)
  if args.verbose:
      print 'Response: {}, reason: {}'.format(conn.status_code, conn.reason)
  if conn.status_code in httpSuccessCodes:
    data = conn.text
    print json.dumps(json.loads(data), sort_keys=True, indent=4)
    # print "Debug test: {}".format(data.message)
  else:
    print 'Response: {}, reason: {}'.format(conn.status_code, conn.reason)
    print 'Non-200 HTTP response seen. Something went awry.'
    data = conn.text
    print json.dumps(json.loads(data), sort_keys=True, indent=4)

except ValueError as e:
  print 'Got the following data back: {}'.format(data)
  print 'JSON parse error: {}'.format(e)
  exit(1)

except requests.exceptions.ConnectionError as e:
  print 'ERROR: Connection Error raised'
  print "|-> Tried to access '{}'".format(request_url)
  print '|-> Error text was:: {}'.format(e)
  exit(1)

except requests.exceptions.HTTPError as e:
  print 'ERROR: HTTP Error raised'
  print "|-> Tried to access '{}'".format(request_url)
  print '|-> Error text was: {}'.format(e)
  exit(1)

except socket.error as e:
  print 'ERROR: Socket Error'
  print "|-> Tried to access '{}'".format(request_url)
  print '|-> Error text was: {}'.format(e)
  exit(1)