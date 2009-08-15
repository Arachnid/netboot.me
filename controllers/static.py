import base
import os

from google.appengine.ext import webapp

class StaticFileHandler(base.BaseHandler):
  def get(self, filename):
    path = os.path.join('static', filename)
    if os.path.exists(path):
      self.response.headers['Content-Type'] = 'application/octet-stream'
      fh = open(path)
      self.response.out.write(fh.read())
      fh.close()
    else:
      self.error(404)
