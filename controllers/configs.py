import base
import models

from django import newforms as forms

class EditConfigForm(forms.Form):
  name = forms.CharField(max_length=255)
  description = forms.CharField(widget=forms.widgets.Textarea())
  deprecated = forms.BooleanField(required=False)

class CreateConfigForm(forms.Form):
  name = forms.CharField(max_length=255)
  description = forms.CharField(widget=forms.widgets.Textarea())
  type = forms.ChoiceField(
      widget=forms.widgets.Select(attrs={'id':"imagetype"}),
      choices=(
        ("kernel", "Linux Kernel"),
        ("image", "Raw image file"),
        ("memdisk", "Disk image")),
      initial="kernel")
  kernel = forms.URLField(widget=forms.widgets.TextInput(attrs={'id':"kernel"}),
                          label="Kernel/Image")
  initrd = forms.URLField(widget=forms.widgets.TextInput(attrs={'id':"initrd"}),
                          required=False)
  args = forms.CharField(widget=forms.widgets.TextInput(attrs={'id':"args"}),
                         required=False)

config_model_map = {
    "kernel": models.KernelBootConfiguration,
    "image": models.ImageBootConfiguration,
    "memdisk": models.MemdiskBootConfiguration,
}

def hasConfig(fun):
  def decorate(self, id, *args, **kwargs):
    config = models.BootConfiguration.get_by_id(int(id))
    if not config:
      self.error(404)
    else:
      fun(self, config, *args, **kwargs)
  return decorate

def ownsConfig(fun):
  @base.loggedIn
  @hasConfig
  def decorate(self, config, *args, **kwargs):
    if self.user.is_admin or (config.user and config.user.key() != self.user.key()):
      fun(self, config, *args, **kwargs)
    else:
      self.error(401)
  return decorate

class BootConfigHandler(base.BaseHandler):
  """Serves up pages for individual configurations."""
  @hasConfig
  def get(self, config):
    if self.isGpxe():
      self.redirect("/%s/boot.gpxe" % (config.key().id(),))
      return
    template_values = self.getTemplateValues()
    template_values['config'] = config
    self.renderTemplate("index.html", template_values)

class EditConfigHandler(base.BaseHandler):
  """Allows editing of a configuration."""
  @ownsConfig
  def get(self, config):
    form = EditConfigForm({
        'name': config.name,
        'description': config.description,
        'deprecated': config.deprecated,
    })
    self.renderForm(config, form)

  @ownsConfig
  def post(self, config):
    form = EditConfigForm(self.request.POST)
    if form.is_valid():
      config.name = form.clean_data['name']
      config.description = form.clean_data['description']
      config.deprecated = bool(form.clean_data['deprecated'])
      config.put()
      self.redirect("/%d" % (config.key().id(),))
    else:
      self.renderForm(config, form)
  
  def renderForm(self, config, form):
    template_values = self.getTemplateValues()
    template_values['config'] = config
    template_values['form'] = form
    self.renderTemplate("edit.html", template_values)

class NewConfigHandler(base.BaseHandler):
  """Create new configurations."""
  @base.loggedIn
  def get(self):
    self.renderForm(CreateConfigForm())
  
  @base.loggedIn
  def post(self):
    form = CreateConfigForm(self.request.POST)
    if form.is_valid():
      args = {
          'name': form.clean_data['name'],
          'description': form.clean_data['description'],
          'owner': self.user,
      }
      if form.clean_data['type'] == "kernel":
        args['kernel'] = form.clean_data['kernel']
        args['initrd'] = form.clean_data['initrd']
        args['args'] = form.clean_data['args']
      elif form.clean_data['type'] in ("image", "memdisk"):
        args['image'] = form.clean_data['kernel']
      config = config_model_map[form.clean_data['type']](**args)
      config.put()
      self.redirect('/%d' % (config.key().id(),))
    else:
      self.renderForm(form)
  
  def renderForm(self, form):
    template_values = self.getTemplateValues()
    template_values['form'] = form
    self.renderTemplate("create.html", template_values)

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
