from django.urls import include, path, re_path

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
    path(
        "settings/initial",
        settings.InitialSettings.as_view(),
        name="settings.initial",
    ),
    path("settings/log", settings.LogView.as_view(), name="settings.log"),
    path("settings/about", settings.AboutByroView.as_view(), name="settings.about"),
    path(
        "settings/registration",
        settings.RegistrationConfigView.as_view(),
        name="settings.registration",
    ),
    path("settings/users/", users.UserListView.as_view(), name="settings.users.list"),
    path(
        "settings/users/add",
        users.UserCreateView.as_view(),
        name="settings.users.add",
    ),
    path(
        "settings/users/<int:pk>/",
        users.UserDetailView.as_view(),
        name="settings.users.detail",
    ),
    path("settings", settings.ConfigurationView.as_view(), name="settings.base"),
    path("", dashboard.DashboardView.as_view(), name="dashboard"),
    path(
        "members/typeahead",
        members.MemberListTypeaheadView.as_view(),
        name="members.typeahead",
    ),
    path("members/list", members.MemberListView.as_view(), name="members.list"),
    path(
        "members/list/export",
        members.MemberListExportView.as_view(),
        name="members.list.export",
    ),
    path(
        "members/list/import",
        members.MemberListImportView.as_view(),
        name="members.list.import",
    ),
    path(
        "members/list/disclosure",
        members.MemberDisclosureView.as_view(),
        name="members.disclosure",
    ),
    path(
        "members/list/balance",
        members.MemberBalanceView.as_view(),
        name="members.balance",
    ),
    path("members/add", members.MemberCreateView.as_view(), name="members.add"),
    path(
        "members/view/<int:pk>/",
        include(
            [
                path("data", members.MemberDataView.as_view(), name="members.data"),
                path(
                    "timeline",
                    members.MemberTimelineView.as_view(),
                    name="members.timeline",
                ),
                path(
                    "finance",
                    members.MemberFinanceView.as_view(),
                    name="members.finance",
                ),
                path(
                    "operations",
                    members.MemberOperationsView.as_view(),
                    name="members.operations",
                ),
                path(
                    "record-disclosure",
                    members.MemberRecordDisclosureView.as_view(),
                    name="members.record-disclosure",
                ),
                path("log", members.MemberLogView.as_view(), name="members.log"),
                path("mails", members.MemberMailsView.as_view(), name="members.mails"),
                path(
                    "documents",
                    members.MemberDocumentsView.as_view(),
                    name="members.documents",
                ),
                path(
                    "", members.MemberDashboardView.as_view(), name="members.dashboard"
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
    path("accounts/", accounts.AccountListView.as_view(), name="finance.accounts.list"),
    path(
        "accounts/add",
        accounts.AccountCreateView.as_view(),
        name="finance.accounts.add",
    ),
    path(
        "accounts/<int:pk>/",
        accounts.AccountDetailView.as_view(),
        name="finance.accounts.detail",
    ),
    path(
        "accounts/<int:pk>/delete",
        accounts.AccountDeleteView.as_view(),
        name="finance.accounts.delete",
    ),
    path("mails/<int:pk>", mails.MailDetail.as_view(), name="mails.mail.view"),
    path("mails/<int:pk>/copy", mails.MailCopy.as_view(), name="mails.mail.copy"),
    path(
        "mails/<int:pk>/delete",
        mails.OutboxPurge.as_view(),
        name="mails.mail.delete",
    ),
    path(
        "mails/<int:pk>/send",
        mails.OutboxSend.as_view(),
        name="mails.mail.send",
    ),
    path("mails/compose", mails.Compose.as_view(), name="mails.compose"),
    path("mails/sent", mails.SentMail.as_view(), name="mails.sent"),
    path("mails/outbox", mails.OutboxList.as_view(), name="mails.outbox.list"),
    path("mails/outbox/send", mails.OutboxSend.as_view(), name="mails.outbox.send"),
    path("mails/outbox/purge", mails.OutboxPurge.as_view(), name="mails.outbox.purge"),
    path("mails/templates", mails.TemplateList.as_view(), name="mails.templates.list"),
    path(
        "mails/templates/add",
        mails.TemplateCreate.as_view(),
        name="mails.templates.add",
    ),
    path(
        "mails/templates/<int:pk>",
        mails.TemplateDetail.as_view(),
        name="mails.templates.view",
    ),
    path(
        "templates/<int:pk>/delete",
        mails.TemplateDelete.as_view(),
        name="mails.templates.delete",
    ),
]
