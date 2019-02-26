from django.conf.urls import include, url

from . import views


member_pages = [
    url(r'^$', views.MemberView.as_view(), name='member.dashboard'),
    url(r'^update$', views.MemberUpdateView.as_view(), name='member.update'),
    url(r'^member_list$', views.MemberListView.as_view(), name='member.list'),
]

urlpatterns = [
    url(r'^member/(?P<secret_token>[^/]+)/', include((member_pages, 'memberpage'))),
]
app_name = 'public'
