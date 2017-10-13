from django.conf.urls import url

from .views import DashboardView

office_urls = [
    url('^$', DashboardView.as_view(), name='dashboard'),
]
