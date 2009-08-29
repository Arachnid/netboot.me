import base
import logging
import models
import urlparse

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

# Min version of ordinary gPXE that doesn't need upgrading
MIN_GPXE_VER = (999, 0, 0) # All versions currently require upgrading
# Min version of netboot.me gPXE that doesn't need upgrading
MIN_NETBOOTME_VER = (0, 1, None)

class GpxeHandler(base.BaseHandler):
  """Serves up gPXE scripts to boot the category menu."""
  def get(self):
    gpxe_ver, netbootme_ver = self.getGpxeVersions()
    logging.warn("%s %s", netbootme_ver, netbootme_ver < MIN_NETBOOTME_VER)
    if netbootme_ver[0] is not None:
      if netbootme_ver < MIN_NETBOOTME_VER:
        # netboot.me gPXE that's too old
        self.serveUpgrade()
      else:
        self.serveMenu()
    elif gpxe_ver[0] is not None and gpxe_ver < MIN_GPXE_VER:
      # regular gPXE that's too old
      self.serveUpgrade()
    else:
      # up to date version, or unrecognised UA
      self.serveMenu()
  
  def serveMenu(self):
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

  def serveUpgrade(self):
    self.response.headers['Content-Type'] = 'text/plain'
    self.response.out.write("#!gpxe\n")
    self.response.out.write("echo\n")
    self.response.out.write(
        "echo Your copy of gPXE is too old. "
        "Upgrade at netboot.me to avoid seeing this every boot!\n")
    self.response.out.write("chain http://static.netboot.me/gpxe/netbootme.kpxe\n")
    

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

def writeEntry(menu, depth, label, entry, default=False):
  makeLine(menu, depth, "label %s", label)
  if default:
    makeLine(menu, depth + 1, "menu default")
  makeLine(menu, depth + 1, "menu label %s", entry.name)
  makeLine(menu, depth + 1, "text help")
  menu.append(word_wrap("(%s) %s" % (entry.get_sources(),
                                     entry.description)))
  makeLine(menu, depth + 1, "endtext")
  menu.extend(("  "*(depth+1)) + x for x in entry.generateMenuEntry())


class MenuEntry(object):
  def __init__(self, category, entries):
    self.category = category
    self.subcategories = []
    self.entries = [entries[x] for x in category.entries]

  def getPopular(self, num=2, entries=False):
    all_entries = [y for x in self.subcategories
                   for y in x.getPopular(num, True)]
    if entries:
      all_entries.extend(self.entries)
    all_entries.sort(key=lambda x:x.downloads, reverse=True)
    return all_entries[:num]

  def writeMenu(self, menu, depth=0, menupath='', first=False):
    if menupath:
      makeLine(menu, depth - 1, "menu begin %s", menupath[1:])
      if first:
        makeLine(menu, depth, "menu default")
      makeLine(menu, depth, "menu title %s", self.category.name)
      makeLine(menu, depth, "label %s.back", menupath[1:])
      makeLine(menu, depth + 1, "menu label Back...")
      makeLine(menu, depth + 1, "menu exit")
      makeLine(menu, depth, "menu separator")
    # Subcategories
    for i, category in enumerate(self.subcategories):
      category.writeMenu(menu, depth + 1, menupath + (".%d" % i), i==0)
    if self.subcategories:
      # Separator, most popular, separator
      makeLine(menu, depth + 1, "menu separator")
      for i, entry in enumerate(self.getPopular()):
        writeEntry(menu, depth, "%s.p%d" % (menupath, i), entry)
      if self.entries:
        makeLine(menu, depth + 1, "menu.separator")
    # Entries
    for i, entry in enumerate(self.entries):
      writeEntry(menu, depth, "%s.e%d" % (menupath, i), entry,
                 default=not self.subcategories and not i)
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
  def get(self):
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
