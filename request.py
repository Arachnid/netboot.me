import config
import os
import webob

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from controllers import *

application = webapp.WSGIApplication([
  # Homepage
  ('/', IndexHandler),
  ('/(gettingstarted|help)', DocHandler),

  # Category page
  ('/browse(/(?:[a-zA-Z][a-zA-Z0-9]*/)*)', CategoryHandler),
  ('/browse(/(?:[a-zA-Z][a-zA-Z0-9]*/)*)(add|edit|delete)', CategoryActionHandler),

  # Gpxe script (loads category menu)
  ('/browse(/(?:[a-zA-Z][a-zA-Z0-9]*/)*)menu.gpxe|/menu.gpxe', GpxeHandler), 

  # Category menu definition
  ('/browse(/(?:[a-zA-Z][a-zA-Z0-9]*/)*)menu.cfg|/menu.cfg', MenuHandler),

  # Individual boot entry page
  ('/([0-9]+)', BootConfigHandler),
  ('/([0-9]+)/edit', EditConfigHandler),
  
  # List of a user's configs
  ('/my/configs', MyConfigsHandler),
  ('/my/newconfig', NewConfigHandler),
  
  # Individual boot gpxe script
  ('/([0-9]+)/boot.gpxe', BootGpxeHandler),
], debug=config.on_dev_server)

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
