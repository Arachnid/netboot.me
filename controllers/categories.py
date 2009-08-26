import base
import logging
import models
import urlparse

from django import newforms as forms
from google.appengine.api import memcache
from google.appengine.ext import db

def word_wrap(s, width=80):
  paragraphs = s.split('\n')
  lines = []
  for paragraph in paragraphs:
    while len(paragraph) > width:
      pos = paragraph.rfind(' ', 0, width)
      if not pos:
        pos = width
      lines.append(paragraph[:pos])
      paragraph = paragraph[pos:]
    lines.append(paragraph)
  return '\n'.join(lines)

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

class GpxeHandler(base.BaseHandler):
  """Serves up gPXE scripts to boot the category menu."""
  def get(self, category):
    if not category:
      category = '/'
    menutype = self.request.GET.get("menutype", "vesa")
    if menutype == "text":
      menufile = "menu.c32"
    else:
      menufile = "vesamenu.c32"
    menupath = category + menufile
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write("#!gpxe\n")
    self.response.out.write("chain %s menu.cfg\n" % (menufile,))

def getCategories(category_name):
  category_name = unicode(category_name)
  q = models.Category.all()
  q.filter('path >=', category_name)
  q.filter('path <', category_name + u'\ufffd')
  q.order('path')
  categories = q.fetch(1000)
  return categories

def getEntries(categories):
  entry_keys = set()
  for category in categories:
    entry_keys.update(category.entries)
  entry_keys = list(entry_keys)
  return dict(zip(entry_keys, db.get(entry_keys)))

def makeLine(menu, depth, format, *args):
  menu.append(("  " * depth) + (format % args))

class MenuEntry(object):
  def __init__(self, category, entries):
    self.category = category
    self.subcategories = []
    self.entries = [entries[x] for x in category.entries]

  def writeMenu(self, menu, depth=0, menupath='', first=False):
    if menupath:
      makeLine(menu, depth - 1, "menu begin %s", menupath[1:])
      if first:
        makeLine(menu, depth, "menu default")
      makeLine(menu, depth, "menu title %s", self.category.name)
      makeLine(menu, depth, "label %s.back", menupath[1:])
      makeLine(menu, depth + 1, "menu label Back...")
      makeLine(menu, depth + 1, "menu exit")
    for i, category in enumerate(self.subcategories):
      category.writeMenu(menu, depth + 1, menupath + (".%d" % i), i==0)
    for i, entry in enumerate(self.entries):
      makeLine(menu, depth, "label %s.e%d", menupath[1:], i)
      if not self.subcategories and i == 0:
        makeLine(menu, depth + 1, "menu default")
      makeLine(menu, depth + 1, "menu label %s", entry.name)
      makeLine(menu, depth + 1, "text help")
      menu.append(word_wrap("(%s) %s" % (entry.get_sources(),
                                         entry.description)))
      makeLine(menu, depth + 1, "endtext")
      menu.extend(("  "*(depth+1)) + x for x in entry.generateMenuEntry())
    if menupath:
      makeLine(menu, depth - 1, "menu end")

def generateMenu(categories, entries):
  stack = []
  for category in categories:
    while stack and not category.path.startswith(stack[-1].category.path):
      stack.pop()
    entry = MenuEntry(category, entries)
    if stack:
      stack[-1].subcategories.append(entry)
    stack.append(entry)
  return stack[0]

def getConfig(category_name):
  categories = getCategories(category_name)
  if not categories:
    return None
  entries = getEntries(categories)
  menu = generateMenu(categories, entries)
  menu_lines = []
  menu.writeMenu(menu_lines)
  return "\n".join(menu_lines)

class MenuHandler(base.BaseHandler):
  """Serves up netboot menu files for the category."""
  def get(self, category_name):
    if not category_name:
      category_name = '/'
    config = memcache.get("menu:%s" % (category_name,))
    if config:
      logging.info("Serving config for %s from memcache", category_name)
    else:
      config = getConfig(category_name)
      memcache.set("menu:%s" % (category_name,), config, time=300)
      logging.info("Regenerating config for %s", category_name)
    if not config:
      self.error(404)
      return
    template_values = self.getTemplateValues()
    template_values['name'] = category_name
    template_values['config'] = config
    self.response.headers['Content-Type'] = 'application/octet-stream'
    self.renderTemplate('menu.cfg', template_values)

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
