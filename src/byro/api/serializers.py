from rest_framework import serializers

from byro.members.models import Member, Membership

AUDIT_FIELDS = {"id", "member", "created", "modified", "created_by", "modified_by"}


def _build_profile_serializer(profile_cls):
    fields = [f.name for f in profile_cls._meta.fields if f.name not in AUDIT_FIELDS]

    meta_cls = type("Meta", (), {"model": profile_cls, "fields": fields})
    return type(
        f"{profile_cls.__name__}Serializer",
        (serializers.ModelSerializer,),
        {"Meta": meta_cls},
    )


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["id", "start", "end", "amount", "interval"]


class MemberSerializer(serializers.ModelSerializer):
    memberships = MembershipSerializer(many=True, read_only=True)
    balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
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
