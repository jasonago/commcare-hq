from django.conf.urls import patterns, url

from corehq.apps.hqcase.views import explode_cases

urlpatterns = patterns('corehq.apps.hqcase.views',
    # for load testing
    url(r'explode/', explode_cases, name='hqcase_explode_cases')
)
