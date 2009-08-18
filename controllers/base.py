import cgi
import logging
import models
import os
import sys
import traceback
import urlparse

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

class BaseHandler(webapp.RequestHandler):
  def initialize(self, request, response):
    super(BaseHandler, self).initialize(request, response)
    self.user = models.UserAccount.get_current()
  
  def getTemplatePath(self, template):
    module = self.__module__.rpartition('.')[2]
    return os.path.join('templates', module , template)
  
  def renderTemplate(self, template_name, template_values):
    path = self.getTemplatePath(template_name)
    self.response.out.write(template.render(path, template_values))

  def getTemplateValues(self):
    return {
        'handler': self.__class__.__name__,
        'user': self.user,
        'auth_url': (users.create_login_url(self.request.url) if not self.user
                     else users.create_logout_url(self.request.url)),
        'path': self.request.path
    }

  def isGpxe(self):
    return self.request.headers.get('User-Agent', '').startswith('gPXE')
