from decimal import Decimal

import django_filters
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from byro.bookkeeping.special_accounts import SpecialAccounts
from byro.documents.models import Document
from byro.members.models import Member, Membership

from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    MemberSerializer,
    MembershipSerializer,
)


class MemberFilter(django_filters.FilterSet):
    email = django_filters.CharFilter(field_name="email", lookup_expr="iexact")
    email__contains = django_filters.CharFilter(
        field_name="email", lookup_expr="icontains"
    )
    number = django_filters.CharFilter(field_name="number", lookup_expr="exact")
    name__contains = django_filters.CharFilter(
        field_name="name", lookup_expr="icontains"
    )
    is_active = django_filters.BooleanFilter(method="filter_is_active")
    secret_token = django_filters.CharFilter(
        field_name="profile_memberpage__secret_token", lookup_expr="exact"
    )

    def filter_is_active(self, queryset, name, value):
        from django.db.models import Q
        from django.utils.timezone import now as tz_now

        today = tz_now().date()
        active_q = Q(memberships__start__lte=today) & (
            Q(memberships__end__isnull=True) | Q(memberships__end__gte=today)
        )
        if value:
            return queryset.filter(active_q).distinct()
        return queryset.exclude(active_q).distinct()

    class Meta:
        model = Member
        fields = []


BALANCE_TYPE_MAP = {
    "payment": lambda: (SpecialAccounts.fees_receivable, SpecialAccounts.bank),
    "initial": lambda: (
        SpecialAccounts.opening_balance,
        SpecialAccounts.fees_receivable,
    ),
    "waiver": lambda: (SpecialAccounts.fees_receivable, SpecialAccounts.lost_income),
}


class MemberViewSet(ModelViewSet):
    queryset = Member.all_objects.all()
    serializer_class = MemberSerializer
    filterset_class = MemberFilter
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def perform_create(self, serializer):
        # Logging is done inside serializer.create()
        serializer.save()

    def perform_update(self, serializer):
        # Logging is done inside serializer.update()
        serializer.save()

    @action(detail=True, methods=["get"])
    def balance(self, request, pk=None):
        member = self.get_object()
        return Response({"balance": member.balance})

    @action(detail=True, methods=["post"], url_path="adjust-balance")
    def adjust_balance(self, request, pk=None):
        member = self.get_object()

        amount_str = request.data.get("amount")
        memo = request.data.get("memo", "")
        balance_type = request.data.get("type", "payment")
        value_datetime_str = request.data.get("value_datetime")

        if amount_str is None:
            return Response(
                {"error": "amount is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            amount = Decimal(str(amount_str))
        except Exception:
            return Response(
                {"error": "invalid amount"}, status=status.HTTP_400_BAD_REQUEST
            )

        if balance_type not in BALANCE_TYPE_MAP:
            return Response(
                {"error": f"type must be one of {list(BALANCE_TYPE_MAP.keys())}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from_, to_ = BALANCE_TYPE_MAP[balance_type]()

        if value_datetime_str:
            from django.utils.dateparse import parse_date, parse_datetime

            value_datetime = parse_datetime(value_datetime_str) or parse_date(
                value_datetime_str
            )
            if value_datetime is None:
                return Response(
                    {"error": "invalid value_datetime"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            from django.utils.timezone import now

            value_datetime = now()

        changed = member.adjust_balance(
            user_or_context=request,
            memo=memo or "API balance adjustment",
            amount=amount,
            from_=from_,
            to_=to_,
            value_datetime=value_datetime,
        )

        if not changed:
            return Response(
                {"error": "no change made (amount was zero)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member.log(
            request, ".finance.balance_adjusted", amount=str(amount), type=balance_type
        )
        return Response({"balance": member.balance})


class MembershipViewSet(ModelViewSet):
    serializer_class = MembershipSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # The member comes from the URL only, and is looked up after the
        # authentication and permission checks
        self.member = get_object_or_404(Member.all_objects, pk=self.kwargs["member_pk"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Membership.objects.none()
        return Membership.objects.filter(member=self.member)

    def perform_create(self, serializer):
        instance = serializer.save(member=self.member)
        request = self.request
        self.member.log(request, ".membership.created", membership_id=instance.pk)
        self.member.update_liabilites()

    def perform_update(self, serializer):
        instance = serializer.save()
        member = instance.member
        request = self.request
        member.log(request, ".membership.updated", membership_id=instance.pk)
        member.update_liabilites()

    def perform_destroy(self, instance):
        member = instance.member
        request = self.request
        member.log(request, ".membership.deleted", membership_id=instance.pk)
        instance.delete()
        member.update_liabilites()


class MemberDocumentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet
):
    serializer_class = DocumentSerializer
    parser_classes = [MultiPartParser]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # The member comes from the URL only, and is looked up after the
        # authentication and permission checks
        self.member = get_object_or_404(Member.all_objects, pk=self.kwargs["member_pk"])

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Document.objects.none()
        return Document.objects.filter(member=self.member)

    @extend_schema(
        request=DocumentUploadSerializer, responses={201: DocumentSerializer}
    )
    def create(self, request, *args, **kwargs):
        serializer = DocumentUploadSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        # Document.save() stores the file, calculates the content hash and
        # logs ".stored". The document and both log entries are created
        # together or not at all, as in the member view of the office.
        with transaction.atomic():
            document = serializer.save(member=self.member)
            self.member.log(
                request,
                ".document.created",
                document=document,
                content_hash=document.content_hash,
            )
        return Response(
            self.get_serializer(document).data, status=status.HTTP_201_CREATED
        )
