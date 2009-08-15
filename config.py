import os

on_dev_server = os.environ['SERVER_SOFTWARE'].startswith('Development')
memdisk_url = "http://static.netboot.me/memdisk"
