import base

class DocHandler(base.BaseHandler):
  def get(self, page):
    self.renderTemplate('%s.html' % page, self.getTemplateValues())
