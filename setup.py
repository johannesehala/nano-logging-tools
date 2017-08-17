"""
nano-logging-tools: nanomsg based logging tools.
"""

from setuptools import setup, find_packages
from os.path import join as pjoin

import moteping

doclines = __doc__.split("\n")

setup(name='nano-logging-tools',
      version=moteping.version,
      description='nanomsg based logging tools',
      long_description='\n'.join(doclines[2:]),
      url='http://github.com/thinnect/nano-logging-tools',
      author='Raido Pahtma',
      author_email='raido@thinnect.com',
      license='MIT',
      platforms=["any"],
      packages=find_packages(),
      install_requires=['nanomsg'],
      scripts=[pjoin('bin', 'nanoprintf-logger'), pjoin('bin', 'nanoprintf-server')],
      zip_safe=False)
