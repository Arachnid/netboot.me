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
    if category != "/":
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
      makeLine(menu, depth + 1, "menu label %s", entry.name)
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
  category, categories = getCategories(category_name)
  if not category:
    return None, None
  entries = getEntries(categories)
  menu = generateMenu(categories, entries)
  menu_lines = []
  menu.writeMenu(menu_lines)
  return category, "\n".join(menu_lines)

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
