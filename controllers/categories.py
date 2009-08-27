import base
import logging
import models
import urlparse

from django import newforms as forms
from google.appengine.api import memcache
from google.appengine.ext import db

class EditCategoryForm(forms.Form):
  name = forms.CharField()
  description = forms.CharField(required=False, widget=forms.widgets.Textarea())

class CreateCategoryForm(EditCategoryForm):
  path = forms.CharField()

class CategoryHandler(base.BaseHandler):
  """Serves end-user category pages, and redirects to GpxeHandler for gPXE."""
  def get(self, category_name):
    if self.isGpxe():
      self.redirect("/browse%s/menu.gpxe" % (category_name,))
      return
    template_values = self.getTemplateValues()
    category = models.Category.get_by_key_name(category_name)
    if not category:
      self.error(404)
      return
    template_values['category'] = category
    template_values['subcategories'] = category.subcategories.fetch(100)
    self.renderTemplate("index.html", template_values)

class CategoryActionHandler(base.BaseHandler):
  ACTION_FORMS = {
      'add': CreateCategoryForm,
      'edit': EditCategoryForm,
      'delete': lambda x=None: None,
  }
  
  @base.isAdmin
  def get(self, category_name, action):
    category = models.Category.get_by_key_name(category_name)
    if not category:
      self.error(404)
      return
    self.renderForm(action, category)

  @base.isAdmin
  def post(self, category_name, action):
    category = models.Category.get_by_key_name(category_name)
    if not category:
      self.error(404)
      return
    form = self.ACTION_FORMS[action](self.request.POST)
    if form and not form.is_valid():
      self.renderForm(action, category, form=None)
    else:
      handler = getattr(self, action)
      handler(category, form)
  
  def renderForm(self, action, category, form=None):
    template = '%s.html' % action
    if not form:
      if action == 'edit':
        args = {
            'name': category.name,
            'description': category.description
        }
      else:
        args = None
      form = self.ACTION_FORMS[action](args)
    template_values = self.getTemplateValues()
    template_values['category'] = category
    template_values['form'] = form
    self.renderTemplate(template, template_values)
  
  def add(self, category, form):
    path = '%s%s/' % (category.path, form.clean_data['path'])
    category = models.Category(
        key_name = path,
        name = form.clean_data['name'],
        description = form.clean_data['description'],
        path = path,
        depth = path.count('/') - 1)
    category.put()
    self.redirect('/browse%s' % (category.path,))
  
  def edit(self, category, form):
    category.name = form.clean_data['name']
    category.description = form.clean_data['description']
    category.put()
    self.redirect('/browse%s' % (category.path,))
  
  def delete(self, category, unused_form):
    category.delete()
    self.redirect('/browse%s/' % (category.path.rsplit('/', 2)[0]))
