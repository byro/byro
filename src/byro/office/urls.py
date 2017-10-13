from django.conf.urls import include, url

from .views import (
    ConfigurationView, DashboardView, MemberCreateView, MemberDashboardView,
    MemberDataView, MemberFinanceView, MemberListView, RegistrationConfigView,
)

office_urls = [
    url('^settings/registration$', RegistrationConfigView.as_view(), name='settings.registration'),
    url('^settings$', ConfigurationView.as_view(), name='settings.base'),
    url('^$', DashboardView.as_view(), name='dashboard'),
    url(r'^members/list', MemberListView.as_view(), name='members.list'),
    url(r'^members/add', MemberCreateView.as_view(), name='members.add'),
    url(r'^members/view/(?P<pk>\d+)/', include([
        url('data$', MemberDataView.as_view(), name='members.data'),
        url('finance$', MemberFinanceView.as_view(), name='members.finance'),
        url('$', MemberDashboardView.as_view(), name='members.dashboard'),
    ])),
]
