from django.conf.urls import include, url

from .views import (
    accounts, dashboard, mails, members, realtransactions, settings, upload,
)

app_name = 'office'
urlpatterns = [
    url('^settings/registration$', settings.RegistrationConfigView.as_view(), name='settings.registration'),
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

    url('^realtransaction/list', realtransactions.RealTransactionListView.as_view(), name='realtransactions.list'),
    url('^realtransaction/match', realtransactions.RealTransactionMatchView.as_view(), name='realtransactions.match'),

    url('^upload/list', upload.UploadListView.as_view(), name='uploads.list'),
    url(r'^upload/process/(?P<pk>\d+)', upload.UploadProcessView.as_view(), name='uploads.process'),
    url(r'^upload/match/(?P<pk>\d+)', upload.UploadMatchView.as_view(), name='uploads.match'),
    url('^upload/add', upload.CsvUploadView.as_view(), name='uploads.add'),

    url('^accounts/$', accounts.AccountListView.as_view(), name='accounts.list'),
    url('^accounts/add$', accounts.AccountCreateView.as_view(), name='accounts.add'),
    url(r'^accounts/(?P<pk>\d+)/$', accounts.AccountDetailView.as_view(), name='accounts.detail'),
    url(r'^accounts/(?P<pk>\d+)/delete$', accounts.AccountDeleteView.as_view(), name='accounts.delete'),

    url('^mails/(?P<pk>[0-9]+)$', mails.MailDetail.as_view(), name='mails.mail.view'),
    url('^mails/(?P<pk>[0-9]+)/copy$', mails.MailCopy.as_view(), name='mails.mail.copy'),
    url('^mails/(?P<pk>[0-9]+)/delete$', mails.OutboxPurge.as_view(), name='mails.mail.delete'),
    url('^mails/(?P<pk>[0-9]+)/send$', mails.OutboxSend.as_view(), name='mails.mail.send'),
    url('^mails/sent$', mails.SentMail.as_view(), name='mails.sent'),
    url('^mails/outbox$', mails.OutboxList.as_view(), name='mails.outbox.list'),
    url('^mails/outbox/send$', mails.OutboxSend.as_view(), name='mails.outbox.send'),
    url('^mails/outbox/purge$', mails.OutboxPurge.as_view(), name='mails.outbox.purge'),

    url('^mails/templates$', mails.TemplateList.as_view(), name='mails.templates.list'),
    url('^mails/templates/new$', mails.TemplateDetail.as_view(), name='mails.templates.create'),
    url('^mails/templates/(?P<pk>[0-9]+)$', mails.TemplateDetail.as_view(), name='mails.templates.view'),
    url('^templates/(?P<pk>[0-9]+)/delete$', mails.TemplateDelete.as_view(), name='mails.templates.delete'),
]
