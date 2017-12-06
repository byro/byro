from django.conf.urls import url

from .views import LoginView, logout_view

app_name = 'common'
urlpatterns = [
    url('^login/$', LoginView.as_view(), name='login'),
    url('^logout/$', logout_view, name='logout'),
]
