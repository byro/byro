from django.conf.urls import include, url

from .views import (
    ConfigurationView, DashboardView, MemberCreateView, MemberDashboardView,
    MemberDataView, MemberFinanceView, MemberListView, RegistrationConfigView,
    RealTransactionListView, AccountListView, AccountDetailView, AccountCreateView,
    AccountDeleteView
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
    url('^realtransaction/list', RealTransactionListView.as_view(), name='realtransactions.list'),
    url('^accounts/$', AccountListView.as_view(), name='accounts.list'),
    url('^accounts/add$', AccountCreateView.as_view(), name='accounts.add'),
    url('^accounts/(?P<pk>\d+)/$', AccountDetailView.as_view(), name='accounts.detail'),
    url('^accounts/(?P<pk>\d+)/delete$', AccountDeleteView.as_view(), name='accounts.delete'),
]
