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

def loggedIn(fun):
  def decorate(self, *args, **kwargs):
    if not self.user:
      self.redirect(users.create_login_url(self.request.url))
    else:
      fun(self, *args, **kwargs)
  return decorate

def isAdmin(fun):
  @loggedIn
  def decorate(self, *args, **kwargs):
    if not self.user.is_admin:
      self.error(401)
    else:
      fun(self, *args, **kwargs)
  return decorate

class BaseHandler(webapp.RequestHandler):
  def initialize(self, request, response):
    super(BaseHandler, self).initialize(request, response)
    self.user = models.UserAccount.get_current()
  
  def getTemplatePath(self, template, module=None):
    if not module:
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
  
  def error(self, code, detail=None):
    self.response.set_status(code)
    template_values = self.getTemplateValues()
    template_values['code'] = code
    template_values['message'] = self.response.http_status_message(code)
    template_values['detail'] = detail
    error_template = self.getTemplatePath("%d.html" % (code,), module="errors")
    if not os.path.exists(error_template):
      error_template = self.getTemplatePath("error.html", module="errors")
    self.response.out.write(template.render(error_template, template_values))

  def isGpxe(self):
    return self.request.headers.get('User-Agent', '').startswith('gPXE')
