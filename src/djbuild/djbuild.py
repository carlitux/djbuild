import logging, os, zc.buildout
import sys
import os

from installer import Installer

class DjBuild(object):

    def __init__(self, buildout, name, options):
        self.log = logging.getLogger(name)
        self.egg = zc.recipe.egg.Egg(buildout, options['recipe'], options)

        self.buildout, self.name, self.options = buildout, name, options
        options['location'] = os.path.join(
            buildout['buildout']['parts-directory'], name)
        options['bin-directory'] = buildout['buildout']['bin-directory']

        options.setdefault('project', 'example.com')
        options.setdefault('external-apps', 'apps')
        options.setdefault('local-apps', 'company')
        options.setdefault('settings', 'development')

        options.setdefault('urlconf', options['project'] + '.urls')
        # Set this so the rest of the recipe can expect the values to be
        # there. We need to make sure that both pythonpath and extra-paths are
        # set for BBB.
        if 'extra-paths' in options:
            options['pythonpath'] = options['extra-paths']
        else:
            options.setdefault('extra-paths', options.get('pythonpath', ''))
            
        # Usefull when using archived versions
        buildout['buildout'].setdefault(
            'download-cache',
            os.path.join(buildout['buildout']['directory'],
                         'downloads'))

        # only try to download stuff if we aren't asked to install from cache
        self.install_from_cache = self.buildout['buildout'].get(
            'install-from-cache', '').strip() == 'true'
        
        self.__installer = Installer(self.options, self.buildout, self.log, self.name)


    def install(self):
        print '\n------------------ Installing DjBuild ------------------\n'
        version = self.options['version']
        location = self.options['location']
        base_dir = self.buildout['buildout']['directory']
        project_dir = os.path.join(base_dir, 'src')
        download_dir = self.buildout['buildout']['download-cache']
        
        # updating sys.path to find django settings
        sys.path.insert(0, project_dir)
        
        extra_path = self.__installer.get_extra_paths()
        requirements, ws = self.egg.working_set(['djbuild'])
        
        self.__installer.verify_or_create_download_dir(download_dir)
        self.__installer.remove_pre_existing_installation(location)
        
        self.__installer.install_django(version, download_dir, location, self.install_from_cache)
        self.__installer.install_recipe(location)
        self.__installer.install_project(project_dir, self.options['project'])
        
        script_paths = self.__installer.install_scripts(extra_path, ws)
        
        print '\n------------------ Installing DjBuild ------------------\n'

        return script_paths + [location]

    def update(self):
        pass
    
