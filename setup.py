from setuptools import setup, find_packages

setup(
  name = 'rst2dep',
  packages = find_packages(),
  version = '1.3.0.1',
  description = 'RST (Rhetorical Structure Theory) constituent and dependency converter for discourse parses',
  author = 'Amir Zeldes',
  author_email = 'amir.zeldes@georgetown.edu',
  package_data = {'':['README.md','LICENSE','requirements.txt'],'rst2dep':['*']},
  install_requires=[],
  url = 'https://github.com/amir-zeldes/rst2dep',
  license='Apache License, Version 2.0',
  download_url = 'https://github.com/amir-zeldes/rst2dep/releases/tag/v1.3.0.1',
  keywords = ['NLP', 'RST', 'discourse', 'dependencies', 'converter', 'conversion','Rhetorical Structure Theory','parsing'],
  classifiers = ['Programming Language :: Python',
'Programming Language :: Python :: 2',
'Programming Language :: Python :: 3',
'License :: OSI Approved :: Apache Software License',
'Operating System :: OS Independent'],
)