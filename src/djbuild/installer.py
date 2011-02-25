import os
import re
import shutil
import urllib2
import templates
import setuptools
import subprocess
import zc.recipe.egg

from zc.buildout import UserError
from dist_installer import install

class Installer:
    
    def __init__(self, options, buildout, log, name):
        self.options = options
        self.buildout = buildout
        self.log = log
        self.name = name
    
    def install_svn_version(self, version, download_dir, location,
                            install_from_cache):
        svn_url = self.version_to_svn(version)
        download_location = os.path.join(
            download_dir, 'django-' +
            self.version_to_download_suffix(version))
        if not install_from_cache:
            if os.path.exists(download_location):
                if self.svn_update(download_location, version):
                    raise UserError(
                        "Failed to update Django; %s. "
                        "Please check your internet connection." % (
                            download_location))
            else:
                self.log.info("Checking out Django from svn: %s" % svn_url)
                cmd = 'svn co %s %s' % (svn_url, download_location)
                if not self.buildout['buildout'].get('verbosity'):
                    cmd += ' -q'
                if self.command(cmd):
                    raise UserError("Failed to checkout Django. "
                                    "Please check your internet connection.")
        else:
            self.log.info("Installing Django from cache: " + download_location)

        shutil.copytree(download_location, location)
        return download_location


    def install_release(self, version, download_dir, tarball, destination):
        extraction_dir = os.path.join(download_dir, 'django-archive')
        setuptools.archive_util.unpack_archive(tarball, extraction_dir)
        # Lookup the resulting extraction dir instead of guessing it
        # (Django releases have a tendency not to be consistend here)
        untarred_dir = os.path.join(extraction_dir,
                                    os.listdir(extraction_dir)[0])
        shutil.move(untarred_dir, destination)
        shutil.rmtree(extraction_dir)
        return destination

    def get_release(self, version, download_dir):
        tarball = os.path.join(download_dir, 'django-%s.tar.gz' % version)

        # Only download when we don't yet have an archive
        if not os.path.exists(tarball):
            download_url = 'http://www.djangoproject.com/download/%s/tarball/'
            self.log.info("Downloading Django from: %s" % (
                    download_url % version))

            tarball_f = open(tarball, 'wb')
            f = urllib2.urlopen(download_url % version)
            tarball_f.write(f.read())
            tarball_f.close()
            f.close()
        return tarball
    
    def is_svn_url(self, version):
        # Search if there is http/https/svn or svn+[a tunnel identifier] in the
        # url or if the trunk marker is used, all indicating the use of svn
        svn_version_search = re.compile(
            r'^(http|https|svn|svn\+[a-zA-Z-_]+)://|^(trunk)$').search(version)
        return svn_version_search is not None

    def version_to_svn(self, version):
        if version == 'trunk':
            return 'http://code.djangoproject.com/svn/django/trunk/'
        else:
            return version

    def version_to_download_suffix(self, version):
        if version == 'trunk':
            return 'svn'
        return [p for p in version.split('/') if p][-1]

    def svn_update(self, path, version):
        command = 'svn up'
        revision_search = re.compile(r'@([0-9]*)$').search(
            self.options['version'])

        if revision_search is not None:
            command += ' -r ' + revision_search.group(1)
        self.log.info("Updating Django from svn")
        if not self.buildout['buildout'].get('verbosity'):
            command += ' -q'
        return self.command(command, cwd=path)

    def get_extra_paths(self):
        basic_dir = os.path.join(self.buildout['buildout']['directory'], 'src')
        local_apps_dir = os.path.join(basic_dir, self.options['project'], self.options['local-apps'])
        external_apps_dir = os.path.join(basic_dir, self.options['project'], self.options['external-apps'])
        extra_paths = [self.options['location'],
                       basic_dir, # now insert into extra path basic dir project
                       local_apps_dir, external_apps_dir]

        # Add libraries found by a site .pth files to our extra-paths.
        if 'pth-files' in self.options:
            import site
            for pth_file in self.options['pth-files'].splitlines():
                pth_libs = site.addsitedir(pth_file, set())
                if not pth_libs:
                    self.log.warning(
                        "No site *.pth libraries found for pth_file=%s" % (
                         pth_file,))
                else:
                    self.log.info("Adding *.pth libraries=%s" % pth_libs)
                    self.options['extra-paths'] += '\n' + '\n'.join(pth_libs)

        pythonpath = [p.replace('/', os.path.sep) for p in
                      self.options['extra-paths'].splitlines() if p.strip()]

        extra_paths.extend(pythonpath)
        
        return extra_paths
    
    def command(self, cmd, **kwargs):
        output = subprocess.PIPE
        if self.buildout['buildout'].get('verbosity'):
            output = None
        command = subprocess.Popen(
            cmd, shell=True, stdout=output, **kwargs)
        return command.wait()

    def create_file(self, file, template, options=None):
        f = open(file, 'w')
        if options is not None:
            f.write(template % options)
        else:
            f.write(template)
        f.close()
    
    def create_manage_script(self, extra_paths, ws):
        project = self.options.get('projectegg', self.options['project'])
        return zc.buildout.easy_install.scripts(
            [(self.options.get('control-script', self.name),
              'djbuild.manage', 'main')],
            ws, self.options['executable'], self.options['bin-directory'],
            extra_paths = extra_paths,
            arguments= "'%s.project.%s.settings'" % (project,
                                                     self.options['settings']))
    
    def create_test_runner(self, extra_paths, working_set):
        apps = self.options.get('test', '').split()
        # Only create the testrunner if the user requests it
        if apps:
            return zc.buildout.easy_install.scripts(
                [(self.options.get('testrunner', 'test'),
                  'djangorecipe.test', 'main')],
                working_set, self.options['executable'],
                self.options['bin-directory'],
                extra_paths = extra_paths,
                arguments= "'%s.project.%s.settings', %s" % (
                    self.options['project'],
                    self.options['settings'],
                    ', '.join(["'%s'" % app for app in apps])))
        else:
            return []
        
    def make_scripts(self, extra_paths, ws):
        scripts = []
        _script_template = zc.buildout.easy_install.script_template
        for protocol in ('wsgi', 'fcgi'):
            zc.buildout.easy_install.script_template = getattr(templates, protocol)
            project = self.options.get('projectegg',  self.options['project'])
            
            scripts.extend(
                zc.buildout.easy_install.scripts(
                    [('%s.%s' % (self.options.get('project', self.name), protocol),
                      '', '')],
                    ws,
                    self.options['executable'],
                    self.options['bin-directory'],
                    extra_paths=extra_paths,
                    arguments= "%s.project.%s.settings" % (project,
                                self.options['settings'])))
        zc.buildout.easy_install.script_template = _script_template
        
        self.create_file("src/%s/deploy/%s.wsgi"%(project, project), templates.wsgi, 
                         {'path': 'os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "%s"),\n  os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "%s")'%(self.options['local-apps'], self.options['external-apps']),
                          'arguments': "%s.project.%s.settings"%(project,
                                                                 self.options['settings'])})
        
        self.create_file("src/%s/deploy/%s.fcgi"%(project, project), templates.wsgi, 
                         {'path': 'os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "%s"),\n  os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "%s")'%(self.options['local-apps'], self.options['external-apps']),
                          'arguments': "%s.project.%s.settings"%(project,
                                                                 self.options['settings'])})
        
        return scripts
    
    def create_project(self, project_dir, project):
        old_config = self.buildout._read_installed_part_options()[0]
        if self.name in old_config:
            old_config = old_config[self.name]
        
            if 'project' in old_config and\
               old_config['project'] != self.options['project']:
                self.log.warning("DjBuild: creating new project '%s', to replace previous project '%s'"%(self.options['project'], old_config['project']))
        
        # saving current work directory
        old_cwd = os.getcwd()
        os.chdir(project_dir)
        
        # importing current django instalation
        import django.core.management
        argv = ['django-admin', 'startproject', project]
        utility = django.core.management.ManagementUtility(argv)
        utility.execute()
        
        self.log.info('DjBuild: creating basic structure')
        os.chdir(project)
        
        os.makedirs('docs')
        os.makedirs('tests')
        os.makedirs('uploads')
        os.makedirs('deploy')
                
        os.makedirs('static/css')
        os.makedirs('static/js')
        os.makedirs('static/images')
        
        os.makedirs('project/development')
        os.makedirs('project/production')
        os.makedirs('project/testing')
        
        self.create_file('tests/__init__.py', '', {})
        self.create_file('project/__init__.py', '', {})
        self.create_file('project/development/__init__.py', '', {})
        self.create_file('project/production/__init__.py', '', {})
        self.create_file('project/testing/__init__.py', '', {})
        
        self.create_file("project/development/settings.py", templates.development_settings, {'project':self.options['project']})
        self.create_file("project/production/settings.py", templates.production_settings, {'project':self.options['project']})
        self.create_file("project/testing/settings.py", templates.testing_settings, {'project':self.options['project']})
        
        self.create_file("project/development/urls.py", templates.development_urls, {'project':self.options['project']})
        self.create_file("project/production/urls.py", templates.production_urls, {'project':self.options['project']})
        self.create_file("project/testing/urls.py", templates.testing_urls, {'project':self.options['project']})
        
        os.makedirs('templates')
        self.create_file("templates/base.html", templates.base_html)
        self.create_file("templates/404.html", templates.t_404_html)
        self.create_file("templates/500.html", templates.t_500_html)
        
        os.makedirs('logs')
        os.makedirs('logs/development')
        os.makedirs('logs/testing')
        os.makedirs('logs/production')
        
        self.create_file("logs/development/error.log", "")
        self.create_file("logs/testing/error.log", "")
        self.create_file("logs/production/error.log", "")
        
        self.create_file("logs/development/access.log", "")
        self.create_file("logs/testing/access.log", "")
        self.create_file("logs/production/access.log", "")
        
        # updating to original cwd
        os.chdir(old_cwd)
        
    def update_project_structure(self):
        old_config = self.buildout._read_installed_part_options()[0]
        # updating old config to project name
        if self.name in old_config:
            old_config = old_config[self.name]
        
            if 'local-apps' in old_config and\
               old_config['local-apps'] != self.options['local-apps']:
                if os.path.exists(old_config['local-apps']):
                    self.log.info("DjBuild: moving local-apps dir from %s to %s"%(old_config['local-apps'], self.options['local-apps']))
                    shutil.move(old_config['local-apps'], self.options['local-apps'])
                    
            if 'external-apps' in old_config and\
               old_config['external-apps'] != self.options['external-apps']:
                if os.path.exists(old_config['external-apps']):
                    self.log.info("DjBuild: moving external-apps dir from %s to %s"%(old_config['external-apps'], self.options['external-apps']))
                    shutil.move(old_config['external-apps'], self.options['external-apps'])
            
        if not os.path.exists(self.options['local-apps']):
            self.log.info("DjBuild: creating local-apps dir %s"%(self.options['local-apps']))
            os.makedirs(self.options['local-apps'])
            
        if not os.path.exists(self.options['external-apps']):
            self.log.info("DjBuild: creating external-apps dir %s"%(self.options['external-apps']))
            os.makedirs(self.options['external-apps'])
            
        answer = raw_input("Do you want to install/update apps?(yes/no): ")
        
        if answer.lower() == 'yes':
            print '\n************** Intalling django apps **************\n'
            apps = self.options.get('apps', '').split()
            if len(apps) == 0:
                self.log.info('No apps to install')
            else:
                install_dir = os.path.abspath(self.options['external-apps'])
                args = ['-U', '-b', self.buildout['buildout']['download-cache'], '-d', install_dir]
                links = self.options.get('find-links', '').split()
                
                if len(links)>0:
                    links.insert(0, '-f')
                    args.extend(links)
                    
                args.extend(apps)
                install(args)
            print '\n************** Intalling django apps **************\n'
            
        print'\n************** Searching for apps config **************\n'
        
        os.environ["DJANGO_SETTINGS_MODULE"] = '%s.project.%s.settings' % (self.options['project'], self.options['settings'])
               
        from django.conf import settings
        
        apps = os.listdir(self.options['external-apps'])
        local_apps = os.listdir(self.options['local-apps'])
        
        # apps into external apps 
        dne = [ x for x in settings.INSTALLED_APPS[:] if x.find('.') == -1 and x not in local_apps] # django and not external
        end = [] # external and not django
        
        del local_apps
        
        for app in apps:
            if app not in settings.INSTALLED_APPS:
                end.append(app)
            elif app in dne:
                dne.remove(app)
        
        # searching for installed apps into djando but not into external-apps directory
       
        if len(end) > 0:
            self.log.warning('These sources apps are installed but not used into django project: \n\t* %s\n'%'\n\t* '.join(end))
                
        # searching for non installed apps into djando but installed into external-apps directory
        if len(dne) > 0:
            self.log.warning('These apps are installed into django but source not installed: \n\t* %s'%'\n\t* '.join(dne))
            
        if len(dne) == 0 and len(end) == 0:
            self.log.info('\nAll is synced')
        
        print '\n************** Searching for apps config **************\n'
        
        del os.environ["DJANGO_SETTINGS_MODULE"]
    
    def verify_or_create_download_dir(self, download_dir):
        if not os.path.exists(download_dir):
            os.mkdir(download_dir)
            
    def remove_pre_existing_installation(self, location):
        # Remove a pre-existing installation if it is there
        if os.path.exists(location):
            shutil.rmtree(location)
            
    def install_django(self, version, download_dir, location, install_from_cache):
        path = ''
        if self.is_svn_url(version):
            path = self.install_svn_version(version, download_dir, location,
                                            install_from_cache)
        else:
            tarball = self.get_release(version, download_dir)
            # Extract and put the dir in its proper place
            path = self.install_release(version, download_dir, tarball, location)
        # updating path to import django
        import sys
        sys.path.insert(0, path)
            
    def install_recipe(self, location):
        self.options['setup'] = location
        development = zc.recipe.egg.Develop(self.buildout,
                                            self.options['recipe'],
                                            self.options)
        development.install()
        del self.options['setup']
        
    def install_project(self, project_dir, project):
        if not self.options.get('projectegg'):
            if not os.path.exists(os.path.join(project_dir, project)):
                self.create_project(project_dir, project)
            else:
                self.log.info(
                    'Skipping creating of project: %(project)s since '
                    'it exists' % self.options)
                
            # creating structure
            old_cwd = os.getcwd()
            os.chdir(os.path.join(project_dir, project))
            
            self.update_project_structure()
            
            os.chdir(old_cwd)
                
    def install_scripts(self, extra_path, ws):
        script_paths = []

        # Create the Django management script
        script_paths.extend(self.create_manage_script(extra_path, ws))

        ## Create the test runner
        script_paths.extend(self.create_test_runner(extra_path, ws))

        ## Make the wsgi and fastcgi scripts if enabled
        script_paths.extend(self.make_scripts(extra_path, ws))
        
        return script_paths
