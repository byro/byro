from django.urls import include, re_path

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
    re_path(
        "^settings/initial$",
        settings.InitialSettings.as_view(),
        name="settings.initial",
    ),
    re_path("^settings/log$", settings.LogView.as_view(), name="settings.log"),
    re_path(
        "^settings/about$", settings.AboutByroView.as_view(), name="settings.about"
    ),
    re_path(
        "^settings/registration$",
        settings.RegistrationConfigView.as_view(),
        name="settings.registration",
    ),
    re_path(
        "^settings/users/$", users.UserListView.as_view(), name="settings.users.list"
    ),
    re_path(
        "^settings/users/add$",
        users.UserCreateView.as_view(),
        name="settings.users.add",
    ),
    re_path(
        r"^settings/users/(?P<pk>\d+)/$",
        users.UserDetailView.as_view(),
        name="settings.users.detail",
    ),
    re_path("^settings$", settings.ConfigurationView.as_view(), name="settings.base"),
    re_path("^$", dashboard.DashboardView.as_view(), name="dashboard"),
    re_path(
        r"^members/typeahead$",
        members.MemberListTypeaheadView.as_view(),
        name="members.typeahead",
    ),
    re_path(r"^members/list$", members.MemberListView.as_view(), name="members.list"),
    re_path(
        r"^members/list/export$",
        members.MemberListExportView.as_view(),
        name="members.list.export",
    ),
    re_path(
        r"^members/list/import$",
        members.MemberListImportView.as_view(),
        name="members.list.import",
    ),
    re_path(
        r"^members/list/disclosure$",
        members.MemberDisclosureView.as_view(),
        name="members.disclosure",
    ),
    re_path(
        r"^members/list/balance$",
        members.MemberBalanceView.as_view(),
        name="members.balance",
    ),
    re_path(r"^members/add$", members.MemberCreateView.as_view(), name="members.add"),
    re_path(
        r"^members/view/(?P<pk>\d+)/",
        include(
            [
                re_path("data$", members.MemberDataView.as_view(), name="members.data"),
                re_path(
                    "timeline$",
                    members.MemberTimelineView.as_view(),
                    name="members.timeline",
                ),
                re_path(
                    "finance$",
                    members.MemberFinanceView.as_view(),
                    name="members.finance",
                ),
                re_path(
                    "operations$",
                    members.MemberOperationsView.as_view(),
                    name="members.operations",
                ),
                re_path(
                    "record-disclosure$",
                    members.MemberRecordDisclosureView.as_view(),
                    name="members.record-disclosure",
                ),
                re_path("log$", members.MemberLogView.as_view(), name="members.log"),
                re_path(
                    "mails$", members.MemberMailsView.as_view(), name="members.mails"
                ),
                re_path(
                    "documents$",
                    members.MemberDocumentsView.as_view(),
                    name="members.documents",
                ),
                re_path(
                    "$", members.MemberDashboardView.as_view(), name="members.dashboard"
                ),
            ]
        ),
    ),
    re_path(
        r"^transactions/(?P<pk>\d+)/",
        transactions.TransactionDetailView.as_view(),
        name="finance.transactions.detail",
    ),
    re_path(
        "^upload/list", upload.UploadListView.as_view(), name="finance.uploads.list"
    ),
    re_path(
        r"^upload/process/(?P<pk>\d+)",
        upload.UploadProcessView.as_view(),
        name="finance.uploads.process",
    ),
    re_path(
        r"^upload/match/(?P<pk>\d+)",
        upload.UploadMatchView.as_view(),
        name="finance.uploads.match",
    ),
    re_path("^upload/add", upload.CsvUploadView.as_view(), name="finance.uploads.add"),
    re_path(
        "^documents/add", documents.DocumentUploadView.as_view(), name="documents.add"
    ),
    re_path(
        r"^documents/(?P<pk>\d+)/(?P<filename>[^/]+)",
        documents.DocumentDownloadView.as_view(),
        name="documents.download",
    ),
    re_path(
        r"^documents/(?P<pk>\d+)",
        documents.DocumentDetailView.as_view(),
        name="documents.detail",
    ),
    re_path(
        "^accounts/$", accounts.AccountListView.as_view(), name="finance.accounts.list"
    ),
    re_path(
        "^accounts/add$",
        accounts.AccountCreateView.as_view(),
        name="finance.accounts.add",
    ),
    re_path(
        r"^accounts/(?P<pk>\d+)/$",
        accounts.AccountDetailView.as_view(),
        name="finance.accounts.detail",
    ),
    re_path(
        r"^accounts/(?P<pk>\d+)/delete$",
        accounts.AccountDeleteView.as_view(),
        name="finance.accounts.delete",
    ),
    re_path(
        "^mails/(?P<pk>[0-9]+)$", mails.MailDetail.as_view(), name="mails.mail.view"
    ),
    re_path(
        "^mails/(?P<pk>[0-9]+)/copy$", mails.MailCopy.as_view(), name="mails.mail.copy"
    ),
    re_path(
        "^mails/(?P<pk>[0-9]+)/delete$",
        mails.OutboxPurge.as_view(),
        name="mails.mail.delete",
    ),
    re_path(
        "^mails/(?P<pk>[0-9]+)/send$",
        mails.OutboxSend.as_view(),
        name="mails.mail.send",
    ),
    re_path("^mails/compose$", mails.Compose.as_view(), name="mails.compose"),
    re_path("^mails/sent$", mails.SentMail.as_view(), name="mails.sent"),
    re_path("^mails/outbox$", mails.OutboxList.as_view(), name="mails.outbox.list"),
    re_path(
        "^mails/outbox/send$", mails.OutboxSend.as_view(), name="mails.outbox.send"
    ),
    re_path(
        "^mails/outbox/purge$", mails.OutboxPurge.as_view(), name="mails.outbox.purge"
    ),
    re_path(
        "^mails/templates$", mails.TemplateList.as_view(), name="mails.templates.list"
    ),
    re_path(
        "^mails/templates/add$",
        mails.TemplateCreate.as_view(),
        name="mails.templates.add",
    ),
    re_path(
        "^mails/templates/(?P<pk>[0-9]+)$",
        mails.TemplateDetail.as_view(),
        name="mails.templates.view",
    ),
    re_path(
        "^templates/(?P<pk>[0-9]+)/delete$",
        mails.TemplateDelete.as_view(),
        name="mails.templates.delete",
    ),
]
