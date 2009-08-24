import base
import datetime
import logging
import models

from google.appengine import runtime

class UpdateHandler(base.BaseHandler):
  def get(self):
    self.post()

  def post(self):
    # Apply exponential decay to all records that haven't been updated recently
    threshold = datetime.datetime.now() - datetime.timedelta(hours=6)
    q = models.BootConfiguration.all(keys_only=True)
    q.filter('last_decay <', threshold)
    try:
      for key in q:
        logging.info("Applying download counter decay for id %d", key.id())
        models.BootConfiguration.recordDownloads(key, 0)
    except runtime.DeadlineExceededError:
      logging.warn("Download counter update terminated due to timeout.")
