production_settings = '''from %(project)s.settings import *

# DEBUG = False # is better do this on global settings files, at root project directory

INSTALLED_APPS += (
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

ROOT_URLCONF = '%(project)s.project.production.urls'
'''

production_urls = '''from django.conf.urls.defaults import patterns, include, url

from %(project)s.urls import urlpatterns

urlpatterns += patterns('',
    #(r'^pushinit/', include('myproject.urls')),
)
'''

development_settings = '''from %(project)s.settings import *

import os

DEBUG=True
TEMPLATE_DEBUG=DEBUG

# set this to '' for development it causes problems
# it is used to collect static files on production mode
# not necessary here
STATIC_ROOT = ''

# STATIC_ROOT path should be added in development mode to server those files
STATICFILES_DIRS += (
    os.path.join(SITE_ROOT, 'static'),
)

INSTALLED_APPS += (
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
)

ROOT_URLCONF = '%(project)s.project.development.urls'
'''

development_urls = '''from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.defaults import patterns, include, url

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from %(project)s.urls import urlpatterns

urlpatterns += patterns('',
    #(r'^init/', include('myproject.urls')),
) + staticfiles_urlpatterns() + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
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

ROOT_URLCONF = '%(project)s.project.testing.urls'
'''

testing_urls = '''from django.conf.urls.defaults import patterns, include, url

from %(project)s.urls import urlpatterns

urlpatterns += patterns('',
    #(r'^init/', include('myproject.urls')),
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

base_html = '''{% load i18n %}<!DOCTYPE html>

<!--[if IE 7 ]><html lang="{{ LANGUAGE_CODE }}" class="no-js ie7"> <![endif]-->
<!--[if IE 8 ]><html lang="{{ LANGUAGE_CODE }}" class="no-js ie8"> <![endif]-->
<!--[if IE 9 ]><html lang="{{ LANGUAGE_CODE }}" class="no-js ie9"> <![endif]-->
<!--[if (gt IE 9)|!(IE)]><!--> <html lang="{{ LANGUAGE_CODE }}" class="no-js"> <!--<![endif]-->

<head>

  <meta charset="utf-8">
  
  {% if meta_description %}<meta name="description" content="{{ meta_description }}">{% endif %}
  {% if meta_keywords %}<meta name="keywords" content="{{ meta_keywords }}">{% endif %}
  <meta name="author" content="linkux-it">
  <meta name="robots" content="index, follow">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  
  <!-- favicon 16x16 -->
  <link rel="shortcut icon" href="/{{ STATIC_URL }}images/favicon.ico">
  <!-- apple touch icon 57x57 -->
  <link rel="apple-touch-icon" href="{{ STATIC_URL }}images/favicon.png">
  
  <script type="text/javascript" src="http://code.jquery.com/jquery.min.js"></script> 
  
  <!-- Main style sheet. Change version number in query string to force styles refresh -->
  <!-- Link element no longer needs type attribute -->
  <link rel="stylesheet" href="css/screen.css?v=1.0">

  <!-- Modernizr for feature detection of CSS3 and HTML5; must be placed in the "head" -->
  <!-- Script tag no longer needs type attribute -->
  <script src="js/modernizr-1.6.min.js"></script>

  <!-- Remove the script reference below if you're using Modernizr -->
  <!--[if lt IE 9]>
  <script src="http://html5shiv.googlecode.com/svn/trunk/html5.js"></script>
  <![endif]-->
  
  {% block extra_base_head %}{% endblock %}
  
  {% block extra_head %}{% endblock %}

  <title>HTML5 template{% block title %}{% if title %} | {{ title }}{% endif %}{% endblock %}</title>
  
</head>

<body>
  
  <header>
  </header>

  <footer>
  </footer>
  
</body>

</html>
'''

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
