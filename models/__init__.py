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

class BootConfiguration(polymodel.PolyModel):
  name = db.TextProperty(required=True)
  description = db.TextProperty()
  created = db.DateTimeProperty(required=True, auto_now_add=True)

  def generateMenuEntry(self):
    raise NotImplementedError()
  
  def generateGpxeScript(self):
    raise NotImplementedError()

class KernelBootConfiguration(BootConfiguration):
  kernel = db.LinkProperty(required=True)
  initrd = db.LinkProperty()
  args = db.StringProperty()

  def generateMenuEntry(self):
    return [
        "kernel %s" % (self.kernel,),
        "append initrd=%s %s" % (self.initrd, self.args),
    ]

  def generateGpxeScript(self):
    return [
        "kernel %s %s" % (self.kernel, self.args),
        "initrd %s" % (self.initrd,),
        "boot",
    ]

class MemdiskBootConfiguration(BootConfiguration):
  image = db.LinkProperty(required=True)
  
  def generateMenuEntry(self):
    return [
      "kernel %s" % (config.memdisk_url,),
      "append initrd=%s" % (self.image,),
    ]

  def generateGpxeScript(self):
    return [
      "kernel %s" % (config.memdisk_url,),
      "initrd %s" % (self.image,),
      "boot"
    ]
