import models

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

menu_root = models.Category.create('/', name='netboot.me boot menu')
installers = models.Category.create('/install')
rescue = models.Category.create('/rescue')
linux_installers = models.Category.create('/install/linux')
linux_rescue = models.Category.create('/rescue/linux')
ubuntu_install = models.Category.create('/install/linux/ubuntu')
ubuntu_rescue = models.Category.create('/rescue/linux/ubuntu')
jaunty_install_menu = models.Category.create('/install/linux/ubuntu/jaunty')
jaunty_install_menu.entries = [x.key() for x in [jaunty_install, jaunty_cmdline, jaunty_expert, jaunty_expert_cmdline]]
karmic_install_menu = models.Category.create('/install/linux/ubuntu/karmic')
karmic_install_menu.entries = [x.key() for x in [karmic_install, karmic_cmdline, karmic_expert, karmic_expert_cmdline]]
ubuntu_rescue.entries = [x.key() for x in [jaunty_rescue, karmic_rescue]]
db.put([menu_root, installers, rescue, linux_installers, linux_rescue, ubuntu_install, ubuntu_rescue, jaunty_install_menu, karmic_install_menu])
