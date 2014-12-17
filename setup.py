from setuptools import setup

PACKAGE_NAME = 'funsize'
PACKAGE_VERSION = '0.1'

setup(name=PACKAGE_NAME,
      version=PACKAGE_VERSION,
      description='partial mar webservice',
      long_description='https://wiki.mozilla.org/User:Ffledgling/Senbonzakura',
      classifiers=[],
      author='Anhad Jai Singh',
      author_email='ffledgling@gmail.com',
      url='https://github.com/mozilla/build-funsize',
      license='MPL',
      install_requires=[
          'Flask==0.10.1',
          'celery==3.1.11',
          'requests==2.2.1',
          'boto==2.33.0',
      ],
      packages=[
          'funsize',
          'funsize.backend',
          'funsize.cache',
          'funsize.frontend',
          'funsize.utils',
      ],
      tests_require=[
          'nose',
          'mock'
      ],
      )
