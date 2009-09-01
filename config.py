import os

on_dev_server = os.environ['SERVER_SOFTWARE'].startswith('Development')
memdisk_url = "http://static.netboot.me/memdisk"
memdisk_iso_url = "http://static.netboot.me/memdisk-iso"
analytics_key = "UA-84449-5"
announce_feed = "http://groups.google.com/group/netbootme-announce/feed/atom_v1_0_msgs.xml?num=5"
