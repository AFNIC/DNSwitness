from distutils.core import setup
from distutils.command.install_data import install_data as orig_install_data
import subprocess

# TODO: README and other files, specially module documentations
# TODO: test dependencies
# TODO: delete the Makefile after having reimplemented targets dist and clean

man_pages = [
    'dnsdelve.1'
    ]

class install_data(orig_install_data):
    def run (self):
        # Build the man page. Ideally, should be done in build_data
        # (so the file would not belong to root) but there is
        # install_data and no build_data :-(
        subprocess.call(["pod2man", "dnsdelve.pod", "dnsdelve.1"])
        orig_install_data.run(self)
  
setup(name='DNSdelve',
      version='0.1',
      description='A framework to gather information from the DNS zones delegated by a registry. It loads a list of delegated zones and queries them for various records.',
      author='Stephane Bortzmeyer',
      author_email='bortzmeyer@nic.fr',
      url='http://www.dnsdelve.net/',
      packages = ['DNSdelve'],
      scripts=['dnsdelve.py'],
      data_files=[('man/man1', man_pages)],
      cmdclass={'install_data': install_data}
      )
