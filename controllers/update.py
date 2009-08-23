import base
import datetime
import logging
import models

from google.appengine import runtime
from google.appengine.api import users
from google.appengine.api.labs import taskqueue

@models.transactionize
def updateCounters(key):
  config = models.BootConfiguration.get(key)
  if (not config.last_rollover or
      datetime.datetime.today() - config.last_rollover 
      >= datetime.timedelta(days=1)):
    config.downloads_daily = config.downloads_daily[-6:] + [0]
    config.downloads_7day = sum(config.downloads_daily)
    config.last_rollover = datetime.datetime.now()
    config.put()

def dailyUpdate(last_key=None):
  q = models.BootConfiguration.all(keys_only=True).order('__key__')
  if last_key:
    q.filter('__key__ >=', last_key)
  try:
    for key in q:
      last_key = key
      logging.info("Updating configuration %s", key.id())
      updateCounters(key)
  except runtime.DeadlineExceededError:
    logging.info("Deferring remaining tasks for later")
    taskqueue.add(params={'key': str(last_key)},
                  url='/tasks/dailyupdate')

class UpdateHandler(base.BaseHandler):
  def get(self):
    self.post()

  def post(self):
    if not users.is_current_user_admin():
      self.error(401)
      return
    dailyUpdate(self.request.POST.get('key', None))
