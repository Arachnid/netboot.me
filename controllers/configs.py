import base
import models

class BootConfigHandler(base.BaseHandler):
  """Serves up pages for individual configurations."""
  def get(self, id):
    if self.isGpxe():
      self.redirect("/%s/gpxe" % (id,))
      return
    config = models.BootConfiguration.get_by_id(int(id))
    if not config:
      self.error(404)
      return
    template_values = self.getTemplateValues()
    template_values['config'] = config
    self.renderTemplate("index.html", template_values)

class BootGpxeHandler(base.BaseHandler):
  """Serves up gPXE scripts to boot directly to a given config."""
  def get(self, id):
    config = models.BootConfiguration.get_by_id(int(id))
    if not config:
      self.error(404)
      return
    script = [ "#!gpxe" ]
    script.extend(config.generateGpxeScript())
    self.response.headers['Content-Type'] = "text/plain"
    self.response.out.write("\n".join(script))
