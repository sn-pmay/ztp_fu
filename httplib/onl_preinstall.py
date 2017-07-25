"""
At install time, this script will

1. be extracted into a temporary working directory
2. be imported as a module, in the same process as the installer
   script

Importing the module should not trigger any side-effects.

At the appropriate time during the install (a chrooted invocation
of the installer Python script) will

1. scrape the top-level plugin's namespace for subclasses of
   onl.install.Plugin.Plugin.
   Implementors should declare classes here
   (inheriting from onl.install.Plugin.Plugin) to embed the plugin
   functionality.
2. instantiate an instance of each class, with the installer
   object initialized as the 'installer' attribute
3. invoke the 'run' method (which must be overridden by implementors)
   For a pre-install plugin, the 'mode' argument is set to
   PLUGIN_PREINSTALL.
4. invoke the 'shutdown' method (by default, a no-op)

The 'run' method should return zero on success. In any other case, the
installer terminates.

The 'installer' object has a handle onto the installer ZIP archive
(self.installer.zf) but otherwise the install has not been
started. That is, the install disk has not been
prepped/initialized/scanned yet. As per the ONL installer API, the
installer starts with *no* filesystems mounted, not even the ones from
a prior install.

A pre-install plugin should execute any pre-install actions when
'mode' is set to PLUGIN_PREINSTALL. If 'mode' is set to any other
value, the plugin should ignore it and return zero. The plugin run()
method is invoked multiple times during the installer with different
values of 'mode'. The 'shutdown()' method is called only once.

"""

class Plugin(onl.install.Plugin.Plugin):
  def run(self, mode):
    if mode == self.PLUGIN_PREINSTALL:
      import onl.install.Plugin
      import platform
      from onl.platform.current import OnlPlatform
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
      self.log.info("hello from preinstall plugin")
      # Parsing out the environment variables
      if "onie_disco_siaddr" in os.environ:
        hostname = os.environ("onie_disco_siaddr")
      else:
        self.log.warn("WARN: onie_disco_siaddr not set. ZTP not performed")
        return 0
      if "onie_disco_ip" in os.environ:
        ip_addr = os.environ("onie_disco_ip")
      else:
        self.log.warn("WARN: onie_disco_ip not set. ZTP not performed")
        return 0
      if OnlPlatform.PLATFORM:
        device_hw = OnlPlatform.PLATFORM
      else:
        self.log.warn("WARN: OnlPlatform.MODEL does not seem to be set.")
        device_hw = ""
      if "onie_serial_num" in os.environ:
        device_sn = os.environ("onie_serial_num")
      else:
        self.log.warn("WARN: onie_serial_num not set. Onie issue on this HW platform?")
        device_sn = "9999999"
      device_os = os.uname()[2]
      device_data = dict(
        ip_addr       = device_ip,
        os_name       = device_os,
        serial_number = device_sn,
        hw_model      = device_hw,
        os_version    = platform.platform(terse=1),
        message       = "preinstall.py",
        state         = "OS-INSTALL"
      )
      # Need to convert the dict to a json object for the httplib connection later
      json_string = json.dumps(device_data)

      port             = '8080'
      protocol         = 'http'
      method           = 'POST'
      httpSuccessCodes = [200, 201, 202, 204]
      verbose          = True
      statuses         = [
        'START', 'DONE', 'CONFIG', 'AWAIT-ONLINE', 'AWAIT-SYSTEM-READY', 
        'OS-INSTALL', 'OS-REBOOTING', 'FAILED'
      ]
      if verbose:
        self.log.info("****** Verbose mode ****")
        self.log.info("DeviceData:".format(device_data))
      
      def delete_device():
        conn.request('DELETE', '/api/devices?ip_addr={}'.format(device_ip))
        r1 = conn.getresponse()
        data = r1.read()
        print json.dumps(json.loads(data), sort_keys=True, indent=4)

      try:
        conn = httplib.HTTPConnection(URL_BASE)
        if verbose: 
          logging.basicConfig(level=logging.DEBUG)
          conn.set_debuglevel(11)
          HTTPConnection.debuglevel = 1
        conn.request(method, URL, json_string, url_headers)
        r1 = conn.getresponse()
        if verbose:
          print "Response: {}, reason: {}".format(r1.status, r1.reason)
        if r1.status in httpSuccessCodes:
          data = r1.read()
          ztp_message = json.loads(data)['message']
          if ztp_message == "device already exists":
            delete_device
            print "Now, lets re-try the add:"
            device_data['message'] = "WARN: Device was alredy in ZTP DB. Deleted and re-added. ({}|{}|{}|{})".format(device_ip, device_os, device_sn, time.time())
            json_string = json.dumps(device_data)
            print json_string
            conn.request(method, URL, json_string, url_headers)
            r1 = conn.getresponse()
            data = r1.read()
          if not ztp_message == "device added":
            print "Adding device to ZTP didn't succeed:"
            print json.dumps(json.loads(data), sort_keys=True, indent=4)
        else:
          print "Response: {}, reason: {}".format(r1.status, r1.reason)
          print "Non-200 HTTP response seen. Something went awry."
          data = r1.read()
          print json.dumps(json.loads(data), sort_keys=True, indent=4)
      except ValueError as e:
        print "Got the following data back: {}".format(data)
        print "JSON parse error: {}".format(e)
        return 0
      except socket.error as e:
        print "ERROR: Socket Error"
        print "Tried to access 'http://{}'".format(URL_BASE)
        print "ERROR: {}".format(e)
        return 0
      return 0
    return 0