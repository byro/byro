from django.conf.urls import include, url

from .views import (
    accounts, dashboard, mails, members, settings, transactions, upload, users,
)

app_name = 'office'
urlpatterns = [
    url('^settings/plugins$', settings.PluginsView.as_view(), name='settings.plugins'),
    url('^settings/registration$', settings.RegistrationConfigView.as_view(), name='settings.registration'),
    url('^settings/users/$', users.UserListView.as_view(), name='settings.users.list'),
    url('^settings/users/add$', users.UserCreateView.as_view(), name='settings.users.add'),
    url(r'^settings/users/(?P<pk>\d+)/$', users.UserDetailView.as_view(), name='settings.users.detail'),
    url('^settings$', settings.ConfigurationView.as_view(), name='settings.base'),
    url('^$', dashboard.DashboardView.as_view(), name='dashboard'),
    url(r'^members/typeahead', members.MemberListTypeaheadView.as_view(), name='members.typeahead'),
    url(r'^members/list', members.MemberListView.as_view(), name='members.list'),
    url(r'^members/add', members.MemberCreateView.as_view(), name='members.add'),
    url(r'^members/view/(?P<pk>\d+)/', include([
        url('data$', members.MemberDataView.as_view(), name='members.data'),
        url('finance$', members.MemberFinanceView.as_view(), name='members.finance'),
        url('leave$', members.MemberLeaveView.as_view(), name='members.leave'),
        url('$', members.MemberDashboardView.as_view(), name='members.dashboard'),
    ])),

    url(r'^transactions/(?P<pk>\d+)/', transactions.TransactionDetailView.as_view(), name='finance.transactions.detail'),

    url('^upload/list', upload.UploadListView.as_view(), name='finance.uploads.list'),
    url(r'^upload/process/(?P<pk>\d+)', upload.UploadProcessView.as_view(), name='finance.uploads.process'),
    url(r'^upload/match/(?P<pk>\d+)', upload.UploadMatchView.as_view(), name='finance.uploads.match'),
    url('^upload/add', upload.CsvUploadView.as_view(), name='finance.uploads.add'),

    url('^accounts/$', accounts.AccountListView.as_view(), name='finance.accounts.list'),
    url('^accounts/add$', accounts.AccountCreateView.as_view(), name='finance.accounts.add'),
    url(r'^accounts/(?P<pk>\d+)/$', accounts.AccountDetailView.as_view(), name='finance.accounts.detail'),
    url(r'^accounts/(?P<pk>\d+)/delete$', accounts.AccountDeleteView.as_view(), name='finance.accounts.delete'),

    url('^mails/(?P<pk>[0-9]+)$', mails.MailDetail.as_view(), name='mails.mail.view'),
    url('^mails/(?P<pk>[0-9]+)/copy$', mails.MailCopy.as_view(), name='mails.mail.copy'),
    url('^mails/(?P<pk>[0-9]+)/delete$', mails.OutboxPurge.as_view(), name='mails.mail.delete'),
    url('^mails/(?P<pk>[0-9]+)/send$', mails.OutboxSend.as_view(), name='mails.mail.send'),
    url('^mails/sent$', mails.SentMail.as_view(), name='mails.sent'),
    url('^mails/outbox$', mails.OutboxList.as_view(), name='mails.outbox.list'),
    url('^mails/outbox/send$', mails.OutboxSend.as_view(), name='mails.outbox.send'),
    url('^mails/outbox/purge$', mails.OutboxPurge.as_view(), name='mails.outbox.purge'),

    url('^mails/templates$', mails.TemplateList.as_view(), name='mails.templates.list'),
    url('^mails/templates/add$', mails.TemplateCreate.as_view(), name='mails.templates.add'),
    url('^mails/templates/(?P<pk>[0-9]+)$', mails.TemplateDetail.as_view(), name='mails.templates.view'),
    url('^templates/(?P<pk>[0-9]+)/delete$', mails.TemplateDelete.as_view(), name='mails.templates.delete'),

]
