import base
import logging
import models
import urlparse

from google.appengine.ext import db

class CategoryHandler(base.BaseHandler):
  """Serves end-user category pages, and redirects to GpxeHandler for gPXE."""
  def get(self, category):
    logging.debug(category)
    if category == '/browse':
      category = '/'
    if self.isGpxe():
      self.redirect("%s/gpxe" % (category,))
      return
    if not category.endswith('/'):
      self.redirect("%s/" % (category,))
      return
    category = category[:-1]
    template_values = self.getTemplateValues()
    category = models.Category.get_by_key_name(category)
    template_values['category'] = category
    template_values['subcategories'] = category.subcategories.fetch(100)
    self.renderTemplate("index.html", template_values)

class GpxeHandler(base.BaseHandler):
  """Serves up gPXE scripts to boot the category menu."""
  def get(self, category):
    menutype = self.request.GET.get("menutype", "vesa")
    if menutype == "text":
      menufile = "menu.c32"
    else:
      menufile = "vesamenu.c32"
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
  if categories and categories[0].path == category_name:
    return categories[0], categories
  else:
    return None, categories

def getEntries(categories):
  entry_keys = set()
  for category in categories:
    entry_keys.update(category.entries)
  entry_keys = list(entry_keys)
  return dict(zip(entry_keys, db.get(entry_keys)))

def generateMenu(base_path, i, depth, categories, entries, write):
  category = categories[i]
  if base_path != '/':
    write(depth, "menu begin %d" % (i,))
    write(depth + 1, "menu title %s" % (category.name,))
    write(depth + 1, "label %d_back" % (i,))
    write(depth + 2, "menu label Back...")
    write(depth + 2, "menu exit")
  if category.path == base_path:
    for entry_key in category.entries:
      entry = entries[entry_key]
      write(depth, "label %d_%d" % (i, entry_key.id()))
      write(depth + 1, "menu label %s" % (entry.name,))
      write(depth + 1, entry.generateMenuEntry())
  i += 1
  while i < len(categories) and categories[i].path.startswith(base_path):
    i = generateMenu(categories[i].path, i, depth + 1, categories, entries,
                     write)
  if base_path != '/':
    write(depth, "menu end")
  return i

def getConfig(category_name):
  category, categories = getCategories(category_name)
  if not category:
    return None, None
  entries = getEntries(categories)
  config_lines = []
  def write_config_line(depth, lines):
    if not isinstance(lines, list):
      lines = [lines]
    config_lines.extend("%s%s" % (" " * depth * 2, x) for x in lines)
  generateMenu('/', 0, -1, categories, entries, write_config_line)
  return category, '\n'.join(config_lines)

class MenuHandler(base.BaseHandler):
  """Serves up netboot menu files for the category."""
  def get(self, category_name):
    category, config = getConfig(category_name)
    if not category:
      self.error(404)
      return
    template_values = self.getTemplateValues()
    template_values['category'] = category
    template_values['config'] = config
    self.response.headers['Content-Type'] = 'application/octet-stream'
    self.renderTemplate('menu.cfg', template_values)
