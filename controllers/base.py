import cgi
import logging
import os
import sys
import traceback
import urlparse

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class BaseHandler(webapp.RequestHandler):
  def getTemplatePath(self, template):
    module = self.__module__.rpartition('.')[2]
    return os.path.join('templates', module , template)
  
  def renderTemplate(self, template_name, template_values):
    path = self.getTemplatePath(template_name)
    self.response.out.write(template.render(path, template_values))

  def getTemplateValues(self):
    return {}

  def isGpxe(self):
    return self.request.headers.get('User-Agent', '').startswith('gPXE')
