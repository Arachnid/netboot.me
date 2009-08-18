import config
import os
import webob

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from controllers import *

application = webapp.WSGIApplication([
  # Homepage
  ('/', IndexHandler),
  ('/(gettingstarted)', DocHandler),

  # Category gpxe script (loads category menu)
  ('(/(?:[a-zA-Z][a-zA-Z0-9]*/)*)menu.gpxe', GpxeHandler), 

  # Category menu definition
  ('(/(?:[a-zA-Z][a-zA-Z0-9]*/)*)menu.cfg', MenuHandler),

  # Individual boot entry page
  ('/([0-9]+)', BootConfigHandler),
  ('/([0-9]+)/edit.do', EditConfigHandler),
  
  # Individual boot gpxe script
  ('/([0-9]+)/boot.gpxe', BootGpxeHandler),

  # Category page
  ('(/(?:[a-zA-Z][a-zA-Z0-9]*/)*|/browse)', CategoryHandler),
], debug=config.on_dev_server)

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
