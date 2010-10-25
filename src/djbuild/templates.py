production_settings = '''
from %(project)s.settings import *

INSTALLED_APPS += (
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)
'''

development_settings = '''
from %(project)s.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG

INSTALLED_APPS += (
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)
'''

testing_settings = '''
from %(project)s.settings import *
DEBUG=True
TEMPLATE_DEBUG=DEBUG

INSTALLED_APPS += (
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)
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

os.environ["DJANGO_SETTINGS_MODULE"] = '%(arguments)s'
from django.conf import settings

from django.core.handlers.wsgi import WSGIHandler
application = WSGIHandler()

'''

fcgi = ''' #!/usr/bin/python

import os
import sys

sys.path[0:0] = [
  %(path)s,
]

os.environ["DJANGO_SETTINGS_MODULE"] = '%(arguments)s'
from django.conf import settings

from django.core.servers.fastcgi import runfastcgi
FCGI_OPTIONS = getattr(settings, 'FCGI_OPTIONS', {})
runfastcgi(FCGI_OPTIONS)
'''

base_html = '''{% load i18n %}
<!DOCTYPE html>
<html>
<head>
    <title>New HTML5 page</title>
</head>
<body>
{% block container %}
<!-- Add your content here-->
{% endblock %}
</body>
</html>'''

t_404_html = '''{% extends 'base.html' %}
{% load i18n %}
{% block container %}
{% trans 'Page Not Found' %}
{% endblock %}''' 

t_500_html = '''{% extends 'base.html' %}
{% load i18n %}
{% block container %}
{% trans 'Server error' %}
{% endblock %}'''
