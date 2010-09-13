##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.

$Id$
"""
import time
import os, shutil, sys, tempfile, urllib2

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')
to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    exec urllib2.urlopen('http://nightly.ziade.org/distribute_setup_dev.py'
                         ).read() in ez
    ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)
    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if len(sys.argv) > 2 and sys.argv[1] == '--version':
    VERSION = '==%s' % sys.argv[2]
    args = sys.argv[3:] + ['bootstrap']
else:
    VERSION = ''
    args = sys.argv[1:] + ['bootstrap']

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse('distribute')).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse('distribute')).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)

# patching zc.buildout.buildout so it uses distribute
from zc.buildout import buildout as zc_buildout
import zc.buildout
import pkg_resources

def _bootstrap(self, args):
    import pkg_resources
    __doing__ = 'Bootstraping.'
    self._setup_directories()
    # Now copy buildout, distribute and setuptools eggs, and record destination eggs:
    entries = []
    for name in 'distribute', 'zc.buildout':
        r = pkg_resources.Requirement.parse(name)
        dist = pkg_resources.working_set.find(r)
        if dist.precedence == pkg_resources.DEVELOP_DIST:
            dest = os.path.join(self['buildout']['develop-eggs-directory'],
                                name+'.egg-link')
            open(dest, 'w').write(dist.location)
            entries.append(dist.location)
        else:
            dest = os.path.join(self['buildout']['eggs-directory'],
                                os.path.basename(dist.location))
            entries.append(dest)
            if not os.path.exists(dest):
                if os.path.isdir(dist.location):
                    shutil.copytree(dist.location, dest)
                else:
                    shutil.copy2(dist.location, dest)

    import sys, time
    egg_directory = self['buildout']['eggs-directory']
    pyver = '%s.%s' % (sys.version_info[0], sys.version_info[1])
    setuptools_name = 'setuptools-0.6c9-py%s.egg' % pyver

    SETUPTOOLS_PKG_INFO  = ['Metadata-Version: 1.0',
                            'Name: setuptools',
                            'Version: 0.6c9',
                            'Summary: xxxx',
                            'Home-page: xxx'
                            'Author: xxx',
                            'Author-email: xxx',
                            'License: xxx',
                            'Description: xxx']
    SETUPTOOLS_PKG_INFO = '\n'.join(SETUPTOOLS_PKG_INFO)
    fake_setuptools = os.path.join(egg_directory, setuptools_name)
    egg_info = os.path.join(fake_setuptools, 'EGG-INFO')
    pkg_info = os.path.join(egg_info, 'PKG-INFO')

    already_patched = False
    if os.path.exists(fake_setuptools):
        # checking if it's a real setuptools or a fake one
        if os.path.exists(pkg_info):
            f = open(pkg_info)
            content = f.read()
            f.close()
            already_patched = content == SETUPTOOLS_PKG_INFO

    if not already_patched:
        if os.path.exists(fake_setuptools):
            new_name = fake_setuptools + '.OLD.%s' % time.time()
            os.rename(fake_setuptools, new_name)

        os.mkdir(fake_setuptools)
        os.mkdir(egg_info)
        f = open(pkg_info, 'w')
        try:
            f.write(SETUPTOOLS_PKG_INFO)
        finally:
            f.close()

    entries.append(fake_setuptools)

    # Create buildout script
    ws = pkg_resources.WorkingSet(entries)
    ws.require('zc.buildout')
    zc.buildout.easy_install.scripts(
        ['zc.buildout'], ws, sys.executable,
        self['buildout']['bin-directory'])
    return True

zc_buildout.Buildout.bootstrap = _bootstrap

zc_buildout.pkg_resources_loc = pkg_resources.working_set.find(
    pkg_resources.Requirement.parse('setuptools')).location

realpath = zc.buildout.easy_install.realpath

def _maybe_upgrade(self):
        __doing__ = 'Checking for upgrades.'
        if not self.newest:
            return
        ws = zc.buildout.easy_install.install(
            [
            (spec + ' ' + self['buildout'].get(spec+'-version', '')).strip()
            for spec in ('zc.buildout', 'setuptools')
            ],
            self['buildout']['eggs-directory'],
            links = self['buildout'].get('find-links', '').split(),
            index = self['buildout'].get('index'),
            path = [self['buildout']['develop-eggs-directory']],
            allow_hosts = self._allow_hosts
            )

        upgraded = []
        for project in 'zc.buildout', 'distribute':
            req = pkg_resources.Requirement.parse(project)
            if ws.find(req) != pkg_resources.working_set.find(req):
                upgraded.append(ws.find(req))

        if not upgraded:
            return

        __doing__ = 'Upgrading.'

        should_run = realpath(
            os.path.join(os.path.abspath(self['buildout']['bin-directory']),
                         'buildout')
            )
        if sys.platform == 'win32':
            should_run += '-script.py'

        if (realpath(os.path.abspath(sys.argv[0])) != should_run):
            self._logger.debug("Running %r.", realpath(sys.argv[0]))
            self._logger.debug("Local buildout is %r.", should_run)
            self._logger.warn("Not upgrading because not running a local "
                              "buildout command.")
            return

        if sys.platform == 'win32' and not self.__windows_restart:
            args = map(zc.buildout.easy_install._safe_arg, sys.argv)
            args.insert(1, '-W')
            if not __debug__:
                args.insert(0, '-O')
            args.insert(0, zc.buildout.easy_install._safe_arg (sys.executable))
            os.execv(sys.executable, args)

        self._logger.info("Upgraded:\n  %s;\nrestarting.",
                          ",\n  ".join([("%s version %s"
                                       % (dist.project_name, dist.version)
                                       )
                                      for dist in upgraded
                                      ]
                                     ),
                          )

        # the new dist is different, so we've upgraded.
        # Update the scripts and return True
        zc.buildout.easy_install.scripts(
            ['zc.buildout'], ws, sys.executable,
            self['buildout']['bin-directory'],
            )

        # Restart
        args = map(zc.buildout.easy_install._safe_arg, sys.argv)
        if not __debug__:
            args.insert(0, '-O')
        args.insert(0, zc.buildout.easy_install._safe_arg (sys.executable))

        if is_jython:
            sys.exit(subprocess.Popen([sys.executable] + list(args)).wait())
        else:
            sys.exit(os.spawnv(os.P_WAIT, sys.executable, args))

zc_buildout.Buildout._maybe_upgrade = _maybe_upgrade

# now calling the bootstrap process as usual
zc_buildout.main(args)
shutil.rmtree(tmpeggs)

