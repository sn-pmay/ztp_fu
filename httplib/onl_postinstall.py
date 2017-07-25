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
   For a post-install plugin, the 'mode' argument is set to
   PLUGIN_POSTINSTALL.
4. invoke the 'shutdown' method (by default, a no-op)

The 'run' method should return zero on success. In any other case, the
installer terminates.

The post-install plugins are invoked after the installer is complete
and after the boot loader is updated.

An exception to this is for proxy GRUB configurations. In that case, the
post-install plugins are invoked after the install is finished, but before
the boot loader has been updated.

At the time the post-install plugin is invoked, none of the
filesystems are mounted. If the implementor needs to manipulate the
disk, the filesystems should be re-mounted temporarily with
e.g. MountContext. The OnlMountContextReadWrite object and their
siblings won't work here because the mtab.yml file is not populated
within the loader environment.

A post-install plugin should execute any post-install actions when
'mode' is set to PLUGIN_POSTINSTALL. If 'mode' is set to any other
value, the plugin should ignore it and return zero. The plugin run()
method is invoked multiple times during the installer with different
values of 'mode'. The 'shutdown()' method is called only once.

When using MountContxt, the system state in the installer object can help
(self.installer.blkidParts in particular).

"""
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
import urlparse
from httplib import HTTPConnection

class Plugin(onl.install.Plugin.Plugin):
  def run(self, mode):
    if mode == self.PLUGIN_POSTINSTALL:
      self.log.info("hello from preinstall plugin")
      if os.environ["onie_exec_url"]:
        parsed = urlparse.parse_qs(urlparse.urlparse(os.environ["onie_exec_url"]).query)
        if "ztp" not in parsed.keys():
          self.log.info("ztp variable not set in the onie_exec_url environment variable. ZTP not called for")
          return 0

      # Parsing out the environment variables
      device_ip = os.environ["onie_disco_ip"]
      device_os = os.uname()[2]
      hostname = os.environ["onie_disco_siaddr"]

      device_data = dict(
        ip_addr       = device_ip,
        os_name       = device_os,
        message       = "ONL postinstall.py",
        state         = "AWAIT-ONLINE"
      )
      # Need to convert the dict to a json object for the httplib connection later
      json_string = json.dumps(device_data)

      port             = '8080'
      protocol         = 'http'
      method           = 'PUT'
      httpSuccessCodes = [200, 201, 202, 204]
      verbose          = True
      statuses         = [
        'START', 'DONE', 'CONFIG', 'AWAIT-ONLINE', 'AWAIT-SYSTEM-READY', 
        'OS-INSTALL', 'OS-REBOOTING', 'FAILED'
      ]
      URL_BASE = '{}:{}'.format(hostname, port)
      URL = '/api/devices/status'
      url_headers = {'Content-Type': 'application/json', 'Accept': 'application/json' }
      request_url="{}://{}{}".format(protocol, URL_BASE, URL)
      if verbose: self.log.info("Request_url: \"{}\"".format(request_url))
      if verbose:
        self.log.info("****** Verbose mode ****")
        self.log.info("DeviceData:".format(json.dumps(device_data)))
      
      try:
        conn = httplib.HTTPConnection(URL_BASE)
        if verbose: 
          logging.basicConfig(level=logging.DEBUG)
          conn.set_debuglevel(11)
          HTTPConnection.debuglevel = 1
        conn.request(method, URL, json_string, url_headers)
        r1 = conn.getresponse()
        if verbose:
          self.log.info("Response: {}, reason: {}".format(r1.status, r1.reason))
        if r1.status in httpSuccessCodes:
          data = r1.read()
          ztp_status = json.loads(data)['ok']
          if not ztp_status:
            self.log.err("ZTP status returned an error:")
            self.log.err(json.dumps(json.loads(data), sort_keys=True, indent=4))
        else:
          self.log.warn("Response: {}, reason: {}".format(r1.status, r1.reason))
          self.log.warn("Non-200 HTTP response seen. Something went awry.")
          data = r1.read()
          self.log.info(json.dumps(json.loads(data), sort_keys=True, indent=4))
      except ValueError as e:
        self.log.err("Got the following data back: {}".format(data))
        self.log.err("JSON parse error: {}".format(e))
        return 0
      except socket.error as e:
        self.log.err("ERROR: Socket Error")
        self.log.err("Tried to access 'http://{}'".format(URL_BASE))
        self.log.err("ERROR: {}".format(e))
        return 0
      return 0
    return 0