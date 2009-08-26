import config
import datetime
import logging
import math
import urlparse

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

def transactionize(fun):
  def decorate(*args, **kwargs):
    return db.run_in_transaction(fun, *args, **kwargs)
  return decorate

class UserAccount(db.Model):
  user = db.UserProperty(required=True)
  is_admin = db.BooleanProperty(required=True, default=False)
  nickname = db.StringProperty(required=True)
  
  @classmethod
  def get_current(cls):
    user = users.get_current_user()
    if not user:
      return None
    return cls.get_or_insert("user:%s" % user.user_id(), user=user,
                             is_admin=users.is_current_user_admin(),
                             nickname=user.nickname().split("@")[0])

class Category(db.Model):
  # An informative name for the category
  name = db.StringProperty(required=True)
  description = db.TextProperty()
  # The / separated path from the root category
  path = db.StringProperty(required=True)
  # The number of components in the path
  depth = db.IntegerProperty(required=True)
  entries = db.ListProperty(db.Key, required=True, default=[])

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
    return [(x, "/".join(parts[:i+2])) for i, x in enumerate(parts[1:-2])]

  @property
  def all_path_tuples(self):
    parts = self.path.split("/")
    return [(x, "/".join(parts[:i+2])) for i, x in enumerate(parts[1:-1])]

def timedelta_to_seconds(delta):
  return delta.days * 86400 + delta.seconds + delta.microseconds / 1000000.0

MEAN_DOWNLOAD_LIFETIME = timedelta_to_seconds(datetime.timedelta(days=7))

class BootConfiguration(polymodel.PolyModel):
  name = db.TextProperty(required=True)
  description = db.TextProperty()
  created = db.DateTimeProperty(required=True, auto_now_add=True)
  owner = db.ReferenceProperty(UserAccount)
  deprecated = db.BooleanProperty(required=True, default=False)
  # 7-day downloads using an exponential decay scheme
  downloads = db.FloatProperty(required=True, default=0.0)
  # Last time downloads was 'decayed'
  last_decay = db.DateTimeProperty(required=True, auto_now_add=True)

  def generateMenuEntry(self):
    return ["kernel /%d/boot.gpxe" % (self.key().id(),)]
  
  def generateGpxeScript(self):
    raise NotImplementedError()
  
  def typeName(self):
    raise NotImplementedError()

  def attributes(self):
    raise NotImplementedError()

  def get_sources(self):
    raise NotImplementedError()

  @property
  def categories(self):
    return Category.all().filter("entries =", self.key())

  @classmethod
  @transactionize
  def recordDownloads(cls, key, count):
    config = BootConfiguration.get(key)
    
    now = datetime.datetime.now()
    decay_time = now - config.last_decay
    decay_fraction = timedelta_to_seconds(decay_time) / MEAN_DOWNLOAD_LIFETIME
    
    config.downloads = config.downloads * (math.e ** -decay_fraction) + count
    logging.warn(config.downloads)
    config.last_decay = now
    config.put()
    return config

def truncateUrl(url):
  parts = url.split("/")
  if len(parts) <= 8:
    return url
  return "/".join(parts[:8]) + "/..."

def formatUrlLink(url):
  return '<a href="%s">%s</a>' % (url, truncateUrl(url))

class KernelBootConfiguration(BootConfiguration):
  kernel = db.LinkProperty(required=True)
  initrd = db.StringProperty()
  args = db.StringProperty()

  def generateGpxeScript(self):
    ret = ["kernel -n img %s %s" % (self.kernel, self.args)]
    if self.initrd:
      ret.append("initrd %s" % (self.initrd,))
    ret.append("boot img")
    return ret

  def typeName(self):
    return "Linux Kernel"
  
  def attributes(self):
    return [
        ("Kernel image", formatUrlLink(self.kernel)),
        ("Initial ramdisk", formatUrlLink(self.initrd)),
        ("Kernel arguments", self.args),
    ]

  def get_sources(self):
    domains = set([
        urlparse.urlparse(self.kernel).netloc,
        urlparse.urlparse(self.initrd).netloc])
    return ', '.join(domains)

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

  def get_sources(self):
    return urlparse.urlparse(self.image).netloc

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

  def get_sources(self):
    return urlparse.urlparse(self.image).netloc

class ISOBootConfiguration(BootConfiguration):
  image = db.LinkProperty(required=True)
  
  def generateGpxeScript(self):
    return [
      "kernel -n img %s iso" % (config.memdisk_url,),
      "initrd -n img %s" % (self.image,),
      "boot img"
    ]

  def typeName(self):
    return "CD ISO image"
  
  def attributes(self):
    return [("ISO location", formatUrlLink(self.image))]

  def get_sources(self):
    return urlparse.urlparse(self.image).netloc
