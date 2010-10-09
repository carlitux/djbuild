
import os
import sys
import shutil
import tempfile

from glob import glob

from distutils import log
from distutils.errors import DistutilsError
from distutils.errors import DistutilsArgError
from distutils.sysconfig import get_config_vars

from setuptools import Command
from setuptools.dist import Distribution
from setuptools.sandbox import run_setup
from setuptools.package_index import URL_SCHEME
from setuptools.archive_util import unpack_archive
from setuptools.package_index import PackageIndex

from pkg_resources import Environment
from pkg_resources import Requirement
from pkg_resources import DEVELOP_DIST
from pkg_resources import normalize_path

class DjDistribution(Distribution):
    def __init__(self, *args, **kwargs):
        Distribution.__init__(self, *args, **kwargs)
        self.cmdclass['DjInstaller'] = DjInstaller
    
    def fetch_build_egg(self, req):
        """Fetch an for sources needed for building"""
        try:
            cmd = self._egg_fetcher
        except AttributeError:
            dist = self.__class__({'script_args':['DjInstaller']})
            dist.parse_config_files()
            opts = dist.get_option_dict('DjInstaller')
            keep = ('find_links', 'index_url')
            for key in opts.keys():
                if key not in keep:
                    del opts[key]   # don't use any other settings
            if self.dependency_links:
                links = self.dependency_links[:]
                if 'find_links' in opts:
                    links = opts['find_links'][1].split() + links
                opts['find_links'] = ('setup', links)
            cmd = DjInstaller(
                dist, args=["x"], install_dir=os.curdir, exclude_scripts=True,
                always_copy=False,
                upgrade=True,
            )
            cmd.ensure_finalized()
            self._egg_fetcher = cmd
        return cmd.easy_install(req)
    
class DjInstaller(Command):
    """Manage a download/build/install process"""
    description = "Find/get/install Python packages"
    command_consumes_arguments = True

    user_options = [
        ("upgrade", "U", "force upgrade (searches PyPI for latest versions)"),
        ("install-dir=", "d", "install package to DIR"),
        ("index-url=", "i", "base URL of Python Package Index"),
        ("find-links=", "f", "additional URL(s) to search for packages"),
        ("download-directory=", "b",
            "download/extract/build in DIR; keep the results"),
    ]
    
    boolean_options = ['upgrade']

    create_index = PackageIndex

    def initialize_options(self):
        self.user = 0

        self.install_dir = None
        self.index_url = None
        self.find_links = None
        self.args = None
        self.upgrade = None
        self.version = None

        # Options not specifiable via command line
        self.package_index = None
        self.download_directory = None
        

        # Always read easy_install options, even if we are subclassed, or have
        # an independent instance created.  This ensures that defaults will
        # always come from the standard configuration file(s)' "easy_install"
        # section, even if this is a "develop" or "install" command, or some
        # other embedding.
        self._dry_run = None
        self.verbose = self.distribution.verbose
        self.distribution._set_command_options(
            self, self.distribution.get_option_dict('DjInstaller')
        )

    def finalize_options(self):
        if self.version:
            print 'distribute %s' % get_distribution('distribute').version
            sys.exit()

        py_version = sys.version.split()[0]

        self.config_vars = {'dist_name': self.distribution.get_name(),
                            'dist_version': self.distribution.get_version(),
                            'dist_fullname': self.distribution.get_fullname(),
                            'py_version': py_version,
                            'py_version_short': py_version[0:3],
                            'py_version_nodot': py_version[0] + py_version[2],
                           }

        self._expand('install_dir')

        normpath = map(normalize_path, sys.path)
        
        self.index_url = self.index_url or "http://pypi.python.org/simple"

        hosts = ['*']
        if self.package_index is None:
            self.package_index = self.create_index(self.index_url, hosts=hosts,)
        self.local_index = Environment(sys.path)

        if self.find_links is not None:
            if isinstance(self.find_links, basestring):
                self.find_links = self.find_links.split()
        else:
            self.find_links = []
        
        self.package_index.add_find_links(self.find_links)
        
        if not self.args:
            raise DistutilsArgError(
                "No urls, filenames, or requirements specified (see --help)")

        self.outputs = []

    def run(self):
        if self.verbose != self.distribution.verbose:
            log.set_verbosity(self.verbose)
        try:
            for spec in self.args:
                self.easy_install(spec)
        finally:
            log.set_verbosity(self.distribution.verbose)

    def easy_install(self, spec, deps=False):
        tmpdir = tempfile.mkdtemp(prefix="djbuild-")
        download = None

        try:
            if not isinstance(spec,Requirement):
                if URL_SCHEME(spec):
                    # It's a url, download it to tmpdir and process
                    download = self.package_index.download(spec, self.download_directory)
                    return self.install_item(None, download, tmpdir, deps)

                elif os.path.exists(spec):
                    # Existing file or directory, just process it directly
                    return self.install_item(None, spec, tmpdir, deps, True)
                else:
                    spec = parse_requirement_arg(spec)

            dist = self.package_index.fetch_distribution(
                spec, self.download_directory, self.upgrade, source=True, local_index=self.local_index
            )

            if dist is None:
                msg = "Could not find suitable distribution for %r" % spec
                raise DistutilsError(msg)
            else:
                return self.install_item(spec, dist.location, tmpdir, deps)

        finally:
            if os.path.exists(tmpdir):
                shutil.rmtree(tmpdir)

    def install_item(self, spec, download, tmpdir, deps):
        log.info("Processing %s", os.path.basename(download))
        dists = self.install_eggs(spec, download, tmpdir)
        
    def install_eggs(self, spec, dist_filename, tmpdir):
        # Anything else, try to extract and build
        setup_base = tmpdir
        if os.path.isfile(dist_filename) and not dist_filename.endswith('.py'):
            unpack_archive(dist_filename, tmpdir, self.unpack_progress)
        elif os.path.isdir(dist_filename):
            setup_base = os.path.abspath(dist_filename)

        # Find the setup.py file
        setup_script = os.path.join(setup_base, 'setup.py')

        if not os.path.exists(setup_script):
            setups = glob(os.path.join(setup_base, '*', 'setup.py'))
            if not setups:
                raise DistutilsError(
                    "Couldn't find a setup script in %s" % os.path.abspath(dist_filename)
                )
            if len(setups)>1:
                raise DistutilsError(
                    "Multiple setup scripts in %s" % os.path.abspath(dist_filename)
                )
            setup_script = setups[0]

        return self.build_and_install(setup_script, setup_base)


    def run_setup(self, setup_script, setup_base, args):
        args = list(args)
        if self.verbose>2:
            v = 'v' * (self.verbose - 1)
            args.insert(0,'-'+v)
        elif self.verbose<2:
            args.insert(0,'-q')
        if self.dry_run:
            args.insert(0,'-n')
        log.info(
            "Running %s %s", setup_script[len(setup_base)+1:], ' '.join(args)
        )
        try:
            run_setup(setup_script, args)
        except SystemExit, v:
            raise DistutilsError("Setup script exited with %s" % (v.args[0],))

    def build_and_install(self, setup_script, setup_base):
        args = ['build']
        try:
            self.run_setup(setup_script, setup_base, args)
            built = os.listdir(setup_base)[0]
            setup_base = os.path.join(setup_base, built, 'build')
            built = os.listdir(setup_base)[0]
            setup_base = os.path.join(setup_base, built)
            to_move = os.listdir(setup_base)
            for m in to_move:
                old = os.path.join(self.install_dir, m)
                if os.path.exists(old):
                    shutil.rmtree(old)
                shutil.move(os.path.join(setup_base, m), self.install_dir)
        finally:
            log.set_verbosity(self.verbose) # restore our log verbosity


    def unpack_progress(self, src, dst):
        # Progress filter for unpacking
        log.debug("Unpacking %s to %s", src, dst)
        return dst     # only unpack-and-compile skips files for dry run

    def _expand(self, *attrs):
        config_vars = self.get_finalized_command('install').config_vars
        from distutils.util import subst_vars
        for attr in attrs:
            val = getattr(self, attr)
            if val is not None:
                val = subst_vars(val, config_vars)
                if os.name == 'posix':
                    val = os.path.expanduser(val)
                setattr(self, attr, val)
                
def parse_requirement_arg(spec):
    try:
        return Requirement.parse(spec)
    except ValueError:
        raise DistutilsError(
            "Not a URL, existing file, or requirement spec: %r" % (spec,)
        )
    
def auto_chmod(func, arg, exc):
    if func is os.remove and os.name=='nt':
        chmod(arg, stat.S_IWRITE)
        return func(arg)
    exc = sys.exc_info()
    raise exc[0], (exc[1][0], exc[1][1] + (" %s %s" % (func,arg)))
    
    
def install(argv=None, **kw):
    from setuptools import setup
    import distutils.core

    USAGE = """\
usage: %(script)s [options] requirement_or_url ...
   or: %(script)s --help
"""

    def gen_usage (script_name):
        script = os.path.basename(script_name)
        return USAGE % vars()

    def with_ei_usage(f):
        old_gen_usage = distutils.core.gen_usage
        try:
            distutils.core.gen_usage = gen_usage
            return f()
        finally:
            distutils.core.gen_usage = old_gen_usage

    class DistributionWithoutHelpCommands(DjDistribution):
        common_usage = ""

        def _show_help(self,*args,**kw):
            with_ei_usage(lambda: DjDistribution._show_help(self,*args,**kw))

        def find_config_files(self):
            files = DjDistribution.find_config_files(self)
            if 'setup.cfg' in files:
                files.remove('setup.cfg')
            return files

    if argv is None:
        argv = sys.argv[1:]

    with_ei_usage(lambda:
        setup(
            script_args = ['-q','DjInstaller', '-v']+argv,
            script_name = sys.argv[0] or 'DjInstaller',
            distclass=DistributionWithoutHelpCommands, **kw
        )
    )

