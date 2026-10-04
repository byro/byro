from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from byro.documents.models import Document, get_document_category_names
from byro.members.models import Member, Membership

AUDIT_FIELDS = {"id", "member", "created", "modified", "created_by", "modified_by"}
# Set by byro when a document is created, never by the client
DOCUMENT_SERVER_FIELDS = ("member", "content_hash")


@extend_schema_field({"type": "string", "format": "decimal", "example": "0.00"})
class BalanceField(serializers.DecimalField):
    pass


@extend_schema_field({"type": "string", "format": "decimal", "example": "10.00"})
class MembershipAmountField(serializers.DecimalField):
    pass


@extend_schema_field(OpenApiTypes.BINARY)
class DocumentFileField(serializers.FileField):
    pass


def _build_profile_serializer(profile_cls):
    fields = [f.name for f in profile_cls._meta.fields if f.name not in AUDIT_FIELDS]

    meta_cls = type("Meta", (), {"model": profile_cls, "fields": fields})
    return type(
        f"{profile_cls.__name__}Serializer",
        (serializers.ModelSerializer,),
        {"Meta": meta_cls},
    )


class MembershipSerializer(serializers.ModelSerializer):
    amount = MembershipAmountField(max_digits=8, decimal_places=2)

    class Meta:
        model = Membership
        fields = ["id", "start", "end", "amount", "interval"]


class MemberSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)
    balance = BalanceField(max_digits=10, decimal_places=2, read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Member
        fields = [
            "id",
            "number",
            "name",
            "address",
            "email",
            "member_contact_type",
            "is_active",
            "balance",
            "memberships",
        ]

    def get_fields(self):
        fields = super().get_fields()
        for profile_cls in Member.profile_classes:
            related_name = profile_cls._meta.get_field(
                "member"
            ).remote_field.get_accessor_name()
            serializer_cls = _build_profile_serializer(profile_cls)
            fields[related_name] = serializer_cls(required=False)
        return fields

    def create(self, validated_data):
        profile_data = {}
        for profile_cls in Member.profile_classes:
            related_name = profile_cls._meta.get_field(
                "member"
            ).remote_field.get_accessor_name()
            if related_name in validated_data:
                profile_data[related_name] = validated_data.pop(related_name)

        member = Member.objects.create(**validated_data)

        request = self.context.get("request")
        member.log(request, ".created")

        for profile_cls in Member.profile_classes:
            related_name = profile_cls._meta.get_field(
                "member"
            ).remote_field.get_accessor_name()
            if related_name in profile_data:
                profile = getattr(member, related_name)
                for attr, value in profile_data[related_name].items():
                    setattr(profile, attr, value)
                profile.save()

        return member

    def update(self, instance, validated_data):
        profile_data = {}
        for profile_cls in Member.profile_classes:
            related_name = profile_cls._meta.get_field(
                "member"
            ).remote_field.get_accessor_name()
            if related_name in validated_data:
                profile_data[related_name] = validated_data.pop(related_name)

        changed_fields = [
            field
            for field, value in validated_data.items()
            if getattr(instance, field) != value
        ]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        request = self.context.get("request")
        if changed_fields:
            instance.log(request, ".updated", changed_fields=changed_fields)

        for profile_cls in Member.profile_classes:
            related_name = profile_cls._meta.get_field(
                "member"
            ).remote_field.get_accessor_name()
            if related_name in profile_data:
                profile = getattr(instance, related_name)
                for attr, value in profile_data[related_name].items():
                    setattr(profile, attr, value)
                profile.save()

        return instance


class DocumentSerializer(serializers.ModelSerializer):
    """A stored document. Documents that were not uploaded through the API can
    lack a title or a date, and their category can come from a plugin that is
    no longer installed."""

    filename = serializers.CharField(source="basename", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "date",
            "category",
            "direction",
            "content_hash",
            "filename",
        ]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.ModelSerializer):
    document = DocumentFileField()

    class Meta:
        model = Document
        fields = ["document", "title", "date", "category", "direction"]
        # The model allows documents without a title or a date, an upload
        # does not. A missing date gets the default of the model.
        extra_kwargs = {
            "title": {"required": True, "allow_null": False},
            "date": {"allow_null": False},
        }

    def get_fields(self):
        fields = super().get_fields()
        fields["category"] = serializers.ChoiceField(
            choices=sorted(get_document_category_names().items()),
            default="byro.documents.misc",
        )
        return fields

    def validate(self, attrs):
        errors = {
            name: ["This field is set by byro and must not be submitted."]
            for name in DOCUMENT_SERVER_FIELDS
            if name in self.initial_data
        }
        if errors:
            raise serializers.ValidationError(errors)
        return attrs
