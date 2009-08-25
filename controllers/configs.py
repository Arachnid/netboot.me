import base
import models

from django import newforms as forms
from google.appengine.api import memcache
from google.appengine.ext import db

class BaseConfigForm(forms.Form):
  name = forms.CharField(max_length=255)
  description = forms.CharField(widget=forms.widgets.Textarea())

class EditConfigForm(BaseConfigForm):
  deprecated = forms.BooleanField(required=False)

class FullEditConfigForm(EditConfigForm):
  kernel = forms.URLField(widget=forms.widgets.TextInput(attrs={'id':"kernel"}),
                          label="Kernel/Image")
  initrd = forms.URLField(widget=forms.widgets.TextInput(attrs={'id':"initrd"}),
                          required=False)
  args = forms.CharField(widget=forms.widgets.TextInput(attrs={'id':"args"}),
                         required=False)

class CreateConfigForm(BaseConfigForm):
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
    if self.user.is_admin or (config.owner and config.owner.key() == self.user.key()):
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
    template_values['categories'] = config.categories.fetch(10)
    template_values['is_admin'] = self.user and self.user.is_admin
    if not self.user:
      template_values['can_edit'] = False
    else:
      is_owner = config.owner and self.user.key() == config.owner.key()
      template_values['can_edit'] = is_owner or self.user.is_admin
    if self.user and self.user.is_admin:
      template_values['category_list'] = [
          x.path for x in models.Category.all().order('path').fetch(1000)]
    self.renderTemplate("index.html", template_values)

class EditConfigHandler(base.BaseHandler):
  """Allows editing of a configuration."""
  @ownsConfig
  def get(self, config):
    form_vals = {
        'name': config.name,
        'description': config.description,
        'deprecated': config.deprecated,
    }
    if isinstance(config, models.KernelBootConfiguration):
      form_vals['kernel'] = config.kernel
      form_vals['initrd'] = config.initrd
      form_vals['args'] = config.args
    else:
      form_vals['kernel'] = config.image
    edit_all = ((self.user and self.user.is_admin) or
                not models.Category.all().filter('entries =', config).count(1))
    if edit_all:
      form = FullEditConfigForm(form_vals)
    else:
      form = EditConfigForm(form_vals)
    self.renderForm(config, form, {'edit_all': edit_all})

  @ownsConfig
  def post(self, config):
    edit_all = ((self.user and self.user.is_admin) or
                not models.Category.all().filter('entries =', config).count(1))
    if edit_all:
      form = FullEditConfigForm(self.request.POST)
    else:
      form = EditConfigForm(self.request.POST)
    if form.is_valid():
      config.name = form.clean_data['name']
      config.description = form.clean_data['description']
      config.deprecated = bool(form.clean_data['deprecated'])
      if edit_all:
        if isinstance(config, models.KernelBootConfiguration):
          config.kernel = form.clean_data['kernel']
          config.initrd = form.clean_data['initrd']
          config.args = form.clean_data['args']
        else:
          config.image = form.clean_data['kernel']
      config.put()
      self.redirect("/%d" % (config.key().id(),))
    else:
      self.renderForm(config, form, {'edit_all': edit_all})
  
  def renderForm(self, config, form, vals=None):
    template_values = self.getTemplateValues()
    if vals:
      template_values.update(vals)
    template_values['config'] = config
    template_values['form'] = form
    self.renderTemplate("edit.html", template_values)

class DeleteConfigHandler(base.BaseHandler):
  @ownsConfig
  def get(self, config):
    template_values = self.getTemplateValues()
    template_values['config'] = config
    template_values['in_menu'] = config.categories.count(1)
    self.renderTemplate("delete.html", template_values)
  
  @ownsConfig
  def post(self, config):
    if config.categories.count(1):
      # In a category - mark deprecated instead
      config.deprecated = True
      config.put()
    else:
      config.delete()
    self.redirect('/my/configs')

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

class MyConfigsHandler(base.BaseHandler):
  @base.loggedIn
  def get(self):
    q = models.BootConfiguration.all()
    q.filter("owner =", self.user)
    all_configs = q.fetch(1000)
    
    template_values = self.getTemplateValues()
    template_values['configs'] = [x for x in all_configs if not x.deprecated]
    template_values['deprecated'] = [x for x in all_configs if x.deprecated]
    self.renderTemplate("myconfigs.html", template_values)

def recordDownload(config):
  # Update a record at most every 10 seconds - otherwise memcache it
  id = config.key().id()
  lock_key = "config_lock:%d" % id
  count_key = "config_downloads:%d" % id
  if memcache.add(lock_key, None, time=10):
    count = int(memcache.get(count_key) or 0) + 1
    models.BootConfiguration.recordDownloads(config.key(), count)
    memcache.delete(count_key)
  else:
    memcache.incr(count_key, initial_value=0)
  
class BootGpxeHandler(base.BaseHandler):
  """Serves up gPXE scripts to boot directly to a given config."""
  @hasConfig
  def get(self, config):
    recordDownload(config)
    script = [ "#!gpxe", "imgfree" ]
    script.extend(config.generateGpxeScript())
    self.response.headers['Content-Type'] = "text/plain"
    self.response.out.write("\n".join(script))

class AddConfigCategoryHandler(base.BaseHandler):
  @hasConfig
  @base.isAdmin
  def post(self, config):
    def add_category():
      category = models.Category.get_by_key_name(self.request.POST['path'])
      category.entries.append(config.key())
      category.put()
    db.run_in_transaction(add_category)
    self.redirect('/%d' % (config.key().id(),))

class DeleteConfigCategoryHandler(base.BaseHandler):
  @hasConfig
  @base.isAdmin
  def post(self, config):
    def remove_category():
      category = models.Category.get_by_key_name(self.request.POST['path'])
      category.entries.remove(config.key())
      category.put()
    db.run_in_transaction(remove_category)
