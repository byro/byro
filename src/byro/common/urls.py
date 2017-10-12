from django.conf.urls import include, url

from .views import LoginView, logout_view

common_urls = [
    url('^login/$', LoginView.as_view(), name='login'),
    url('^logout/$', logout_view, name='logout'),
]
