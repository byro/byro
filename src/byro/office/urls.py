from django.conf.urls import include, url

from .views import (
    accounts,
    dashboard,
    documents,
    mails,
    members,
    settings,
    transactions,
    upload,
    users,
)

app_name = "office"
urlpatterns = [
    url(
        "^settings/initial$",
        settings.InitialSettings.as_view(),
        name="settings.initial",
    ),
    url("^settings/log$", settings.LogView.as_view(), name="settings.log"),
    url("^settings/about$", settings.AboutByroView.as_view(), name="settings.about"),
    url(
        "^settings/registration$",
        settings.RegistrationConfigView.as_view(),
        name="settings.registration",
    ),
    url("^settings/users/$", users.UserListView.as_view(), name="settings.users.list"),
    url(
        "^settings/users/add$",
        users.UserCreateView.as_view(),
        name="settings.users.add",
    ),
    url(
        r"^settings/users/(?P<pk>\d+)/$",
        users.UserDetailView.as_view(),
        name="settings.users.detail",
    ),
    url("^settings$", settings.ConfigurationView.as_view(), name="settings.base"),
    url("^$", dashboard.DashboardView.as_view(), name="dashboard"),
    url(
        r"^members/typeahead$",
        members.MemberListTypeaheadView.as_view(),
        name="members.typeahead",
    ),
    url(r"^members/list$", members.MemberListView.as_view(), name="members.list"),
    url(
        r"^members/list/export$",
        members.MemberListExportView.as_view(),
        name="members.list.export",
    ),
    url(
        r"^members/list/import$",
        members.MemberListImportView.as_view(),
        name="members.list.import",
    ),
    url(
        r"^members/list/disclosure$",
        members.MemberDisclosureView.as_view(),
        name="members.disclosure",
    ),
    url(
        r"^members/list/balance$",
        members.MemberBalanceView.as_view(),
        name="members.balance",
    ),
    url(r"^members/add$", members.MemberCreateView.as_view(), name="members.add"),
    url(
        r"^members/view/(?P<pk>\d+)/",
        include(
            [
                url("data$", members.MemberDataView.as_view(), name="members.data"),
                url(
                    "timeline$",
                    members.MemberTimelineView.as_view(),
                    name="members.timeline",
                ),
                url(
                    "finance$",
                    members.MemberFinanceView.as_view(),
                    name="members.finance",
                ),
                url(
                    "operations$",
                    members.MemberOperationsView.as_view(),
                    name="members.operations",
                ),
                url(
                    "record-disclosure$",
                    members.MemberRecordDisclosureView.as_view(),
                    name="members.record-disclosure",
                ),
                url("log$", members.MemberLogView.as_view(), name="members.log"),
                url("mails$", members.MemberMailsView.as_view(), name="members.mails"),
                url(
                    "documents$",
                    members.MemberDocumentsView.as_view(),
                    name="members.documents",
                ),
                url(
                    "$", members.MemberDashboardView.as_view(), name="members.dashboard"
                ),
            ]
        ),
    ),
    url(
        r"^transactions/(?P<pk>\d+)/",
        transactions.TransactionDetailView.as_view(),
        name="finance.transactions.detail",
    ),
    url("^upload/list", upload.UploadListView.as_view(), name="finance.uploads.list"),
    url(
        r"^upload/process/(?P<pk>\d+)",
        upload.UploadProcessView.as_view(),
        name="finance.uploads.process",
    ),
    url(
        r"^upload/match/(?P<pk>\d+)",
        upload.UploadMatchView.as_view(),
        name="finance.uploads.match",
    ),
    url("^upload/add", upload.CsvUploadView.as_view(), name="finance.uploads.add"),
    url("^documents/add", documents.DocumentUploadView.as_view(), name="documents.add"),
    url(
        r"^documents/(?P<pk>\d+)",
        documents.DocumentDetailView.as_view(),
        name="documents.detail",
    ),
    url(
        "^accounts/$", accounts.AccountListView.as_view(), name="finance.accounts.list"
    ),
    url(
        "^accounts/add$",
        accounts.AccountCreateView.as_view(),
        name="finance.accounts.add",
    ),
    url(
        r"^accounts/(?P<pk>\d+)/$",
        accounts.AccountDetailView.as_view(),
        name="finance.accounts.detail",
    ),
    url(
        r"^accounts/(?P<pk>\d+)/delete$",
        accounts.AccountDeleteView.as_view(),
        name="finance.accounts.delete",
    ),
    url("^mails/(?P<pk>[0-9]+)$", mails.MailDetail.as_view(), name="mails.mail.view"),
    url(
        "^mails/(?P<pk>[0-9]+)/copy$", mails.MailCopy.as_view(), name="mails.mail.copy"
    ),
    url(
        "^mails/(?P<pk>[0-9]+)/delete$",
        mails.OutboxPurge.as_view(),
        name="mails.mail.delete",
    ),
    url(
        "^mails/(?P<pk>[0-9]+)/send$",
        mails.OutboxSend.as_view(),
        name="mails.mail.send",
    ),
    url("^mails/compose$", mails.Compose.as_view(), name="mails.compose"),
    url("^mails/sent$", mails.SentMail.as_view(), name="mails.sent"),
    url("^mails/outbox$", mails.OutboxList.as_view(), name="mails.outbox.list"),
    url("^mails/outbox/send$", mails.OutboxSend.as_view(), name="mails.outbox.send"),
    url("^mails/outbox/purge$", mails.OutboxPurge.as_view(), name="mails.outbox.purge"),
    url("^mails/templates$", mails.TemplateList.as_view(), name="mails.templates.list"),
    url(
        "^mails/templates/add$",
        mails.TemplateCreate.as_view(),
        name="mails.templates.add",
    ),
    url(
        "^mails/templates/(?P<pk>[0-9]+)$",
        mails.TemplateDetail.as_view(),
        name="mails.templates.view",
    ),
    url(
        "^templates/(?P<pk>[0-9]+)/delete$",
        mails.TemplateDelete.as_view(),
        name="mails.templates.delete",
    ),
]
