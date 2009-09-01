import base
import config
import feedparser
import re

from google.appengine.api import memcache
from google.appengine.api import urlfetch

striptags_re = re.compile(r'<[^>]*?>')

def parseAnnouncements(feed):
  ret = []
  for entry in feed.entries:
    ret.append('<li><a href="%s">%s<br /><span>%s</span></a></li>'
               % (entry.link, entry.title, striptags_re.sub('', entry.summary)))
  return "\n".join(ret)

def getAnnouncements():
  try:
    response = urlfetch.fetch(config.announce_feed, deadline=10)
    if response.status_code == 200:
      feed = feedparser.parse(response.content)
      return parseAnnouncements(feed)
  except urlfetch.Error, e:
    logging.exception()
  return None

class IndexHandler(base.BaseHandler):
  def get(self):
    if self.isGpxe():
      self.redirect('/menu.gpxe')
      return
    template_values = self.getTemplateValues()
    announcements = memcache.get('index.html:announcements')
    if not announcements:
      announcements = getAnnouncements()
      memcache.set('index.html:announcements', announcements, time=3600)
    template_values['announcements'] = announcements
    self.renderTemplate('index.html', template_values)

class GettingStartedHandler(base.BaseHandler):
  def get(self):
    self.renderTemplate('gettingstarted.html', self.getTemplateValues())
