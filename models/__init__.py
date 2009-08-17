import config

from google.appengine.ext import db
from google.appengine.ext.db import polymodel

class Category(db.Model):
  # An informative name for the category
  name = db.StringProperty(required=True)
  description = db.TextProperty()
  # The / separated path from the root category
  path = db.StringProperty(required=True)
  # The number of components in the path
  depth = db.IntegerProperty(required=True)
  entries = db.ListProperty(db.Key, required=True, default=[])
  
  @classmethod
  def create(cls, path, name=None):
    path_parts = path.split('/')[1:]
    if not name:
      name = path_parts[-1]
    return cls(key_name=path, path=path, name=name, depth=len(path_parts))

  @property
  def subcategories(self):
    q = Category.all()
    q.filter("path >", self.path)
    q.filter("path <", self.path + u'\ufffd')
    q.filter("depth =", self.depth + 1)
    return q.order('path')

  @property
  def entry_items(self):
    return db.get(self.entries)
  
  @property
  def path_tuples(self):
    parts = self.path.split("/")
    return [(x, "/".join(parts[:i+2])) for i, x in enumerate(parts[1:-1])]

  @property
  def all_path_tuples(self):
    parts = self.path.split("/")
    return [(x, "/".join(parts[:i+2])) for i, x in enumerate(parts[1:])]

class BootConfiguration(polymodel.PolyModel):
  name = db.TextProperty(required=True)
  description = db.TextProperty()
  created = db.DateTimeProperty(required=True, auto_now_add=True)

  def generateMenuEntry(self):
    return ["kernel /%d/boot.gpxe" % (self.key().id(),)]
  
  def generateGpxeScript(self):
    raise NotImplementedError()
  
  def typeName(self):
    raise NotImplementedError()

  def attributes(self):
    raise NotImplementedError()

  @property
  def categories(self):
    return Category.all().filter("entries =", self.key())

def truncateUrl(url):
  parts = url.split("/")
  if len(parts) <= 8:
    return url
  return "/".join(parts[:8]) + "/..."

def formatUrlLink(url):
  return '<a href="%s">%s</a>' % (url, truncateUrl(url))

class KernelBootConfiguration(BootConfiguration):
  kernel = db.LinkProperty(required=True)
  initrd = db.LinkProperty()
  args = db.StringProperty()

  def generateGpxeScript(self):
    return [
        "kernel -n img %s %s" % (self.kernel, self.args),
        "initrd -n img %s" % (self.initrd,),
        "boot img",
    ]

  def typeName(self):
    return "Linux Kernel"
  
  def attributes(self):
    return [
        ("Kernel image", formatUrlLink(self.kernel)),
        ("Initial ramdisk", formatUrlLink(self.initrd)),
        ("Kernel arguments", self.args),
    ]

class ImageBootConfiguration(BootConfiguration):
  image = db.LinkProperty(required=True)
  
  def generateGpxeScript(self):
    return [
      "kernel -n img %s" % (self.image,),
      "boot img"
    ]

  def typeName(self):
    return "Binary image"
  
  def attributes(self):
    return [("Image URL", formatUrlLink(self.image))]

class MemdiskBootConfiguration(BootConfiguration):
  image = db.LinkProperty(required=True)
  
  def generateGpxeScript(self):
    return [
      "kernel -n img %s" % (config.memdisk_url,),
      "initrd -n img %s" % (self.image,),
      "boot img"
    ]

  def typeName(self):
    return "Memdisk"
  
  def attributes(self):
    return [("Memdisk location", formatUrlLink(self.image))]
