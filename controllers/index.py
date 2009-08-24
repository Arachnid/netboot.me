import base

class IndexHandler(base.BaseHandler):
  def get(self):
    if self.isGpxe():
      self.redirect('/menu.gpxe')
      return
    self.renderTemplate('index.html', self.getTemplateValues())

class GettingStartedHandler(base.BaseHandler):
  def get(self):
    self.renderTemplate('gettingstarted.html', self.getTemplateValues())
