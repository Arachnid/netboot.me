import base

class IndexHandler(base.BaseHandler):
  def get(self):
    if self.isGpxe():
      self.redirect('gpxe')
      return
    self.renderTemplate('index.html', self.getTemplateValues())
