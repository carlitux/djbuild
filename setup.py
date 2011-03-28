import os

from setuptools import setup, find_packages

version = '1.0.0'

def read_file(name):
    return open(os.path.join(os.path.dirname(__file__),
                             name)).read()

readme = read_file('README.txt')

setup(name='djbuild',
      version=version,
      description="Buildout recipe for Django",
      long_description='\n\n'.join([readme]),
      classifiers=[
        'Framework :: Buildout',
        'Framework :: Django',
        'Topic :: Software Development :: Build Tools',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: BSD License',
        ],
      package_dir={'': 'src'},
      packages=find_packages('src'),
      keywords='',
      author='Luis C. Cruz',
      author_email='carlitos.kyo@gmail.com',
      url='https://github.com/carlitux/djbuild',
      license='BSD',
      zip_safe=False,
      install_requires=[
        'zc.buildout',
        'zc.recipe.egg',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [zc.buildout]
      default = djbuild:DjBuild
      """,
      )
