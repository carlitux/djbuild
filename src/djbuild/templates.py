production_settings = '''
from %(project)s.settings import *
'''

development_settings = '''
from %(project)s.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG
'''

testing_settings = '''
from %(project)s.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG
'''

wsgi = '''#!/usr/bin/python

import os
import sys

# redirect sys.stdout to sys.stderr for bad libraries like geopy that uses
# print statements for optional import exceptions.
sys.stdout = sys.stderr

sys.path[0:0] = [
  %(path)s,
]

from django.conf import settings
os.environ["DJANGO_SETTINGS_MODULE"] = '%(arguments)s'

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()

'''

fcgi = ''' #!/usr/bin/python

import os
import sys

sys.path[0:0] = [
  %(path)s,
]

from django.conf import settings
os.environ["DJANGO_SETTINGS_MODULE"] = '%(arguments)s'

from django.core.servers.fastcgi import runfastcgi
FCGI_OPTIONS = getattr(settings, 'FCGI_OPTIONS', {})
runfastcgi(FCGI_OPTIONS)
'''