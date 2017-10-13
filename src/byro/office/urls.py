from django.conf.urls import url

from .views import (
    ConfigurationView, DashboardView, MemberCreateView,
    MemberDetailView, MemberListView, RegistrationConfigView,
)

office_urls = [
    url('^settings/registration$', RegistrationConfigView.as_view(), name='settings.registration'),
    url('^settings$', ConfigurationView.as_view(), name='settings'),
    url('^$', DashboardView.as_view(), name='dashboard'),
    url(r'^members/list', MemberListView.as_view(), name='members.list'),
    url(r'^members/add', MemberCreateView.as_view(), name='members.add'),
    url(r'^members/view/(?P<pk>\d+)', MemberDetailView.as_view(), name='members.detail'),
]
