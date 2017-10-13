from django.conf.urls import url

from .views import DashboardView, MemberListView, MemberDetailView

office_urls = [
    url('^$', DashboardView.as_view(), name='dashboard'),
    url(r'^members/list', MemberListView.as_view(), name='members.list'),
    url(r'^members/view/(?P<pk>\d+)', MemberDetailView.as_view(), name='members.detail'),
]
