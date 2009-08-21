import models

def createCategory(path):
  name = path.split('/')[-2]
  if not name:
    name = '/'
  cat = models.Category(key_name=path, path=path, name=name, depth=path.count('/')-1)
  cat.put()
  return cat

kernel = 'http://archive.ubuntu.com/ubuntu/dists/jaunty/main/installer-i386/current/images/netboot/ubuntu-installer/i386/linux'
initrd = 'http://archive.ubuntu.com/ubuntu/dists/jaunty/main/installer-i386/current/images/netboot/ubuntu-installer/i386/initrd.gz'
jaunty_install = models.KernelBootConfiguration(name='Install', description='Regular Ubuntu installer', kernel=kernel, initrd=initrd, args='vga=normal -- quiet')
jaunty_cmdline = models.KernelBootConfiguration(name='Command-line Install', description='Command line Ubuntu installer', kernel=kernel, initrd=initrd, args='tasks=standard pkgsel/language-pack-patterns= pkgsel/install-language-support=false vga=normal -- quiet')
jaunty_expert = models.KernelBootConfiguration(name='Expert Install', description='Expert Ubuntu installer', kernel=kernel, initrd=initrd, args='priority=low vga=normal --')
jaunty_expert_cmdline = models.KernelBootConfiguration(name='Command-line Expert Install', description='Command line Expert Ubuntu installer', kernel=kernel, initrd=initrd, args='tasks=standard pkgsel/language-pack-patterns= pkgsel/install-language-support=false priority=low vga=normal --')
db.put([jaunty_install, jaunty_cmdline, jaunty_expert, jaunty_expert_cmdline])

kernel='http://archive.ubuntu.com/ubuntu/dists/karmic/main/installer-i386/current/images/netboot/ubuntu-installer/i386/linux'
initrd='http://archive.ubuntu.com/ubuntu/dists/karmic/main/installer-i386/current/images/netboot/ubuntu-installer/i386/initrd.gz'
karmic_install = models.KernelBootConfiguration(name='Install', description=jaunty_install.description, kernel=kernel, initrd=initrd, args=jaunty_install.args)
karmic_cmdline = models.KernelBootConfiguration(name=jaunty_cmdline.name, description=jaunty_cmdline.description, kernel=kernel, initrd=initrd, args=jaunty_install.args)
karmic_expert = models.KernelBootConfiguration(name=jaunty_expert.name, description=jaunty_expert.description, kernel=kernel, initrd=initrd, args=jaunty_expert.args)
karmic_expert_cmdline = models.KernelBootConfiguration(name=jaunty_expert_cmdline.name, description=jaunty_expert_cmdline.description, kernel=kernel, initrd=initrd, args=jaunty_expert_cmdline.args)
db.put([karmic_install, karmic_cmdline, karmic_expert, karmic_expert_cmdline])

jaunty_rescue = models.KernelBootConfiguration(name='Jaunty (9.04) x86 rescue', description='Rescue image for Ubuntu Jaunty (9.04) x86', kernel=jaunty_install.kernel, initrd=jaunty_install.initrd, args='vga=normal rescue/enable=true -- quiet')
karmic_rescue = models.KernelBootConfiguration(name='Karmic (9.10) x86 rescue', description='Rescue image for Ubuntu Karmic (9.10) x86', kernel=karmic_install.kernel, initrd=karmic_install.initrd, args=jaunty_rescue.args)
db.put([karmic_rescue, jaunty_rescue])

memtest = models.ImageBootConfiguration(name='Memtest 86', description='Thoroughly tests system memory', image='http://static.netboot.me/memtest/memtest')
db.put(memtest)

menu_root = createCategory('/')
installers = createCategory('/install/')
linux_installers = createCategory('/install/linux/')
ubuntu_install = createCategory('/install/linux/ubuntu/')
jaunty_install_menu = createCategory('/install/linux/ubuntu/jaunty/')
jaunty_install_menu.entries = [x.key() for x in [jaunty_install, jaunty_cmdline, jaunty_expert, jaunty_expert_cmdline]]
karmic_install_menu = createCategory('/install/linux/ubuntu/karmic/')
karmic_install_menu.entries = [x.key() for x in [karmic_install, karmic_cmdline, karmic_expert, karmic_expert_cmdline]]
rescue = createCategory('/rescue/')
linux_rescue = createCategory('/rescue/linux/')
ubuntu_rescue = createCategory('/rescue/linux/ubuntu/')
ubuntu_rescue.entries = [x.key() for x in [jaunty_rescue, karmic_rescue]]
diagnostic_menu = createCategory('/diagnostic/')
diagnostic_menu.entries = [memtest.key()]
db.put([menu_root, installers, rescue, linux_installers, linux_rescue, ubuntu_install, ubuntu_rescue, jaunty_install_menu, karmic_install_menu, diagnostic_menu])
