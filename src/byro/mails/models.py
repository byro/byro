from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import DatabaseError, models, transaction
from django.db.models import Prefetch
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.utils.translation import override
from i18nfield.fields import I18nCharField, I18nTextField

from byro.common.models import LogTargetMixin
from byro.common.models.auditable import Auditable
from byro.common.models.choices import Choices
from byro.common.models.configuration import ByroConfiguration
from byro.mails.send import SendMailException
from byro.members.models import Member


class RecipientType(Choices):
    """Who an :class:`EMail` is addressed to.

    A member is only ever a recipient because the mail says so explicitly:
    ``MEMBER`` mails list their recipients in ``EMail.members``, ``ALL_MEMBERS``
    mails resolve them when they are sent. The addresses of an ``ADDRESS`` mail
    are plain addresses and are never used to find a member, as several
    members may share one address.
    """

    ADDRESS = "addr"
    MEMBER = "member"
    ALL_MEMBERS = "all"


class RecipientsLockedError(ValueError):
    """The recipients of a mail were to be changed after a delivery.

    A mail that has been delivered to somebody is the record of who received
    it: its recipient type, its addresses and its members stay as they are.
    """


class PGPPolicy(Choices):
    SEND_PLAIN = "send_plain"
    BLOCK = "block"


class PGPKeySource(Choices):
    APPLICATION = "application"
    MEMBER_PAGE = "member_page"
    MANUAL_UPLOAD = "manual_upload"
    KEYSERVER = "keyserver"


class PGPKeyStatus(Choices):
    PENDING = "pending"
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    UNVERIFIED = "unverified"


class PGPConfiguration(ByroConfiguration):
    LOG_TARGET_BASE = "byro.settings.pgp"
    settings_template = "office/settings/pgp_configuration_form.html"
    DEFAULT_KEYSERVERS = "\n".join(
        [
            "keys.openpgp.org",
            "keyserver.ubuntu.com",
            "pgp.mit.edu",
        ]
    )

    encryption_enabled = models.BooleanField(
        default=False, verbose_name=_("Encrypt member emails with PGP")
    )
    signing_enabled = models.BooleanField(
        default=False, verbose_name=_("Sign outgoing emails with PGP")
    )
    signing_key_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_("Signing key fingerprint"),
        help_text=_(
            "Fingerprint of the organization's private key in the configured PGP backend."
        ),
    )
    keyserver_url = models.TextField(
        blank=True,
        default=DEFAULT_KEYSERVERS,
        verbose_name=_("Keyserver URLs"),
        help_text=_("Enter one keyserver per line. They are tried in order."),
    )
    missing_key_policy = models.CharField(
        max_length=PGPPolicy.max_length,
        choices=PGPPolicy.choices,
        default=PGPPolicy.SEND_PLAIN,
        verbose_name=_("When no PGP key is available"),
    )
    invalid_key_policy = models.CharField(
        max_length=PGPPolicy.max_length,
        choices=PGPPolicy.choices,
        default=PGPPolicy.BLOCK,
        verbose_name=_("When a PGP key is invalid"),
    )
    unverified_key_policy = models.CharField(
        max_length=PGPPolicy.max_length,
        choices=PGPPolicy.choices,
        default=PGPPolicy.BLOCK,
        verbose_name=_("When a PGP key is unverified"),
    )
    expired_key_policy = models.CharField(
        max_length=PGPPolicy.max_length,
        choices=PGPPolicy.choices,
        default=PGPPolicy.BLOCK,
        verbose_name=_("When a PGP key is expired"),
    )
    refresh_keys_automatically = models.BooleanField(
        default=True, verbose_name=_("Refresh PGP keys automatically")
    )
    key_refresh_interval_days = models.PositiveIntegerField(
        default=1, verbose_name=_("Days between automatic PGP key refreshes")
    )
    keyserver_timeout_seconds = models.PositiveIntegerField(
        default=30, verbose_name=_("Keyserver timeout in seconds")
    )
    send_expiry_reminders = models.BooleanField(
        default=True, verbose_name=_("Remind members before PGP keys expire")
    )
    expiry_reminder_days = models.PositiveIntegerField(
        default=30, verbose_name=_("Days before expiry to send reminders")
    )

    form_title = _("PGP settings")

    def __str__(self):
        return "PGP settings"

    @property
    def keyserver_urls(self):
        return [
            line.strip()
            for line in (self.keyserver_url or self.DEFAULT_KEYSERVERS).splitlines()
            if line.strip()
        ]


class MemberPGPKey(Auditable, models.Model, LogTargetMixin):
    LOG_TARGET_BASE = "byro.members.pgp_key"

    member = models.ForeignKey(
        to="members.Member", related_name="pgp_keys", on_delete=models.CASCADE
    )
    fingerprint = models.CharField(max_length=64, db_index=True)
    public_key = models.TextField(blank=True)
    source = models.CharField(
        max_length=PGPKeySource.max_length,
        choices=PGPKeySource.choices,
        default=PGPKeySource.MANUAL_UPLOAD,
    )
    status = models.CharField(
        max_length=PGPKeyStatus.max_length,
        choices=PGPKeyStatus.choices,
        default=PGPKeyStatus.PENDING,
    )
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_reminder_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ("member", "-is_active", "fingerprint")
        unique_together = (("member", "fingerprint"),)

    def __str__(self):
        return f"{self.member}: {self.fingerprint}"

    def clean(self):
        super().clean()
        from byro.mails.pgp import normalize_fingerprint

        try:
            self.fingerprint = normalize_fingerprint(self.fingerprint)
        except ValueError as e:
            raise ValidationError({"fingerprint": e})

    def save(self, *args, **kwargs):
        self.clean()
        if self.status == PGPKeyStatus.VALID and not self.verified_at:
            self.verified_at = timezone.now()
        return super().save(*args, **kwargs)

    @property
    def is_usable_for_encryption(self):
        return self.is_active and self.status == PGPKeyStatus.VALID


class MailTemplate(Auditable, models.Model):
    subject = I18nCharField(max_length=200, verbose_name=_("Subject"))
    text = I18nTextField(verbose_name=_("Text"))
    reply_to = models.EmailField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_("Reply-To"),
        help_text=_(
            "Change the Reply-To address if you do not want to use the default orga address"
        ),
    )
    bcc = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        verbose_name=_("BCC"),
        help_text=_(
            "Enter comma separated addresses. Will receive a blind copy of every mail sent from this template. This may be a LOT!"
        ),
    )

    def __str__(self):
        return f"{self.subject}"

    def to_mail(
        self,
        email=None,
        locale=None,
        context=None,
        skip_queue=False,
        attachments=None,
        save=True,
        member=None,
    ):
        """Create a mail from this template.

        Pass ``member`` for a mail to a member: the mail then keeps the member
        as its recipient and uses the member's address when it is sent. Pass
        ``email`` for any other address, such as the backoffice address. An
        address is never used to find a member.
        """
        from byro.common.models import Configuration

        if member is not None and email:
            raise ValueError("Pass either a member or an email address, not both.")

        config = Configuration.get_solo()
        locale = locale or config.language
        with override(locale):
            context = context or dict()
            try:
                subject = str(self.subject).format(**context)
                text = str(self.text).format(**context)
            except KeyError as e:
                raise SendMailException(
                    f"Experienced KeyError when rendering Text: {e}"
                )

            if member is not None:
                mail = EMail.for_member(
                    member,
                    reply_to=self.reply_to,
                    bcc=self.bcc,
                    subject=subject,
                    text=text,
                    template=self,
                )
            else:
                mail = EMail(
                    to=email,
                    reply_to=self.reply_to,
                    bcc=self.bcc,
                    subject=subject,
                    text=text,
                    template=self,
                )
            if save:
                mail.save()
                if attachments:
                    for a in attachments:
                        mail.attachments.add(a)
                if skip_queue:
                    mail.send()
        return mail

    def get_absolute_url(self):
        return reverse("office:mails.templates.view", kwargs={"pk": self.pk})

    def get_object_icon(self):
        return mark_safe('<i class="fa fa-envelope-o"></i> ')


def _active_pgp_keys_prefetch():
    return Prefetch(
        "pgp_keys",
        queryset=(
            MemberPGPKey.objects.filter(is_active=True)
            .exclude(status=PGPKeyStatus.NOT_FOUND)
            .order_by("-verified_at", "-last_checked_at", "fingerprint")
        ),
        to_attr="active_pgp_keys",
    )


class EMailQuerySet(models.QuerySet):
    def with_member_recipients(self):
        """Load the member recipients of all mails with one query, for lists
        that show ``EMail.recipient_display``."""
        return self.prefetch_related(
            Prefetch(
                "members",
                queryset=Member.all_objects.order_by("pk"),
                to_attr="prefetched_member_recipients",
            )
        )


class EMail(Auditable, models.Model):
    to_type = models.CharField(
        max_length=RecipientType.max_length,
        choices=(
            (RecipientType.ADDRESS, _("Specific address")),
            (RecipientType.MEMBER, _("Member")),
            (RecipientType.ALL_MEMBERS, _("All members")),
        ),
        default=RecipientType.ADDRESS,
        verbose_name=_("Recipient type"),
    )
    to = models.CharField(
        max_length=1000,
        blank=True,
        verbose_name=_("To"),
        help_text=_("One email address or several addresses separated by commas."),
    )
    reply_to = models.CharField(
        max_length=1000, null=True, blank=True, verbose_name=_("Reply-To")
    )
    cc = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name=_("CC"),
        help_text=_("One email address or several addresses separated by commas."),
    )
    bcc = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        verbose_name=_("BCC"),
        help_text=_("One email address or several addresses separated by commas."),
    )
    subject = models.CharField(max_length=200, verbose_name=_("Subject"))
    # The member recipients: set explicitly for RecipientType.MEMBER, filled
    # while sending for RecipientType.ALL_MEMBERS. Mails sent before the
    # recipient type existed may also carry members here.
    members = models.ManyToManyField(to="members.Member", related_name="emails")
    text = models.TextField(verbose_name=_("Text"))
    sent = models.DateTimeField(null=True, blank=True, verbose_name=_("Sent at"))
    delivered_to = models.JSONField(
        default=list,
        blank=True,
        editable=False,
        verbose_name=_("Delivered to"),
    )
    # Successful deliveries to member recipients: the primary key of the member
    # (as a string, as JSON object keys are strings) and the address that was
    # used. Only ever written by send(); the members relation is no evidence
    # of a delivery.
    delivered_to_members = models.JSONField(
        default=dict,
        blank=True,
        editable=False,
        verbose_name=_("Delivered to members"),
    )
    template = models.ForeignKey(
        to=MailTemplate, null=True, blank=True, on_delete=models.SET_NULL
    )
    attachments = models.ManyToManyField(to="documents.Document", related_name="mails")
    balance = models.ForeignKey(
        to="members.MemberBalance",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reminder_mails",
    )

    objects = EMailQuerySet.as_manager()

    # Member recipients of a mail that is not saved yet, see for_member().
    _pending_member_recipients = None

    @classmethod
    def for_member(cls, member, **kwargs):
        """Return an unsaved mail that is addressed to ``member``.

        ``save()`` stores the mail and its recipient together, so that a
        member mail does not end up without its member.
        """
        mail = cls(to_type=RecipientType.MEMBER, **kwargs)
        mail._pending_member_recipients = [member]
        return mail

    # What identifies the recipients, and what records the deliveries. The
    # members of the mail belong to both and are protected separately.
    RECIPIENT_FIELDS = ("to_type", "to")
    DELIVERY_FIELDS = ("delivered_to", "delivered_to_members")
    # What send() found out. Of a stored mail, these fields are only written
    # by _record_delivery() and _mark_sent(), never by save().
    DELIVERY_STATE_FIELDS = (*DELIVERY_FIELDS, "sent")

    def save(self, *args, **kwargs):
        # save(force_insert, force_update, using, update_fields)
        kwargs.update(
            zip(("force_insert", "force_update", "using", "update_fields"), args)
        )
        if self.to_type != RecipientType.MEMBER:
            # the mail was changed to another recipient type before saving
            self._pending_member_recipients = None
        # Without a primary key the mail is new. So it is with force_insert:
        # the database refuses the insert if the primary key is in use.
        if self.pk is None or kwargs.get("force_insert"):
            return self._save_new(**kwargs)

        with transaction.atomic(using=kwargs.get("using")):
            # With a primary key, the mail is new only if no mail is stored
            # under that key. ``self._state.adding`` does not tell: an object
            # can be built with the primary key of a stored mail, and saving
            # it updates that mail.
            #
            # What may be saved is decided by the stored mail, not by this
            # object: it may have been loaded before a delivery took place, or
            # not have been loaded at all.
            stored = self._lock_stored_state(using=kwargs.get("using"))
            update_fields = kwargs.get("update_fields")
            if stored is None:
                # Nothing is stored that could be updated, which Django would
                # find out as well. It is not left to Django, though: it would
                # update a mail that appeared after the check above.
                if kwargs.get("force_update"):
                    raise DatabaseError("Forced update did not affect any rows.")
                if update_fields is not None:
                    if update_fields:
                        raise DatabaseError(
                            "Save with update_fields did not affect any rows."
                        )
                    return None
                # For the same reason the new mail is inserted, never updated.
                return self._save_new(**{**kwargs, "force_insert": True})
            if _has_deliveries(stored):
                changed = [
                    field
                    for field in self.RECIPIENT_FIELDS
                    if (update_fields is None or field in update_fields)
                    and getattr(self, field) != stored[field]
                ]
                if changed:
                    raise RecipientsLockedError(
                        "The recipients of a mail cannot be changed after a delivery."
                    )
            # Saving never changes what was delivered or whether the mail is
            # sent, not even if update_fields names these fields: this object
            # may be older than the deliveries, and it takes over what is
            # stored instead. Only send() records deliveries.
            for field in self.DELIVERY_STATE_FIELDS:
                setattr(self, field, stored[field])
            super().save(**kwargs)
            if update_fields is None and self._pending_member_recipients:
                # an object from for_member() with the primary key of a stored
                # mail; refused for a delivered mail like any change of members
                self.members.add(*self._pending_member_recipients)
                self._pending_member_recipients = None

    def _save_new(self, **kwargs):
        pending_members = self._pending_member_recipients
        if not pending_members:
            return super().save(**kwargs)

        state = (self.pk, self._state.adding, self._state.db)
        try:
            with transaction.atomic(using=kwargs.get("using")):
                super().save(**kwargs)
                self.members.add(*pending_members)
        except BaseException:
            # nothing was stored: stay unsaved and keep the recipients, so
            # that saving again does not lose them
            self.pk, self._state.adding, self._state.db = state
            raise
        self._pending_member_recipients = None

    def _lock_stored_state(self, using=None):
        """Lock the row of this mail and return its recipients and deliveries
        as they are stored right now, or ``None`` if the mail is not stored.

        Has to be called inside a transaction. The lock makes sure that no
        delivery is recorded between this check and the change it allows.
        """
        return (
            type(self)
            ._base_manager.using(using)
            .select_for_update()
            .filter(pk=self.pk)
            .values(*self.RECIPIENT_FIELDS, *self.DELIVERY_FIELDS, "sent")
            .first()
        )

    def _record_delivery(self, address, member):
        """Store a successful delivery.

        The delivery is added to the deliveries that are stored at this
        moment, not to the ones this object knows, so that a delivery
        recorded by somebody else in the meantime is kept.
        """
        with transaction.atomic():
            stored = self._lock_stored_state()
            delivered_to = [*stored["delivered_to"], address.lower()]
            delivered_to_members = dict(stored["delivered_to_members"])
            if member:
                delivered_to_members[str(member.pk)] = address
            type(self)._base_manager.filter(pk=self.pk).update(
                delivered_to=delivered_to, delivered_to_members=delivered_to_members
            )
            if member:
                # not self.members.add(): the members of a delivered mail are
                # protected, a delivery is the one thing that may extend them
                type(self).members.through.objects.get_or_create(
                    email=self, member=member
                )
        self.delivered_to = delivered_to
        self.delivered_to_members = delivered_to_members

    def _sync_with_stored(self, stored):
        """Take over the recipients and the deliveries of the stored mail."""
        for field in (*self.RECIPIENT_FIELDS, *self.DELIVERY_STATE_FIELDS):
            setattr(self, field, stored[field])
        self.__dict__.pop("prefetched_member_recipients", None)

    def _load_stored_recipients(self, pgp_config):
        """Bring this object up to date with the stored mail and return its
        recipients, see ``_get_recipients()``.

        This object may have been loaded before the recipients of the mail
        were changed or before a delivery. The recipient type, the addresses,
        the members and the deliveries are read together under the lock on the
        mail, so that they belong to one state of the mail.
        """
        with transaction.atomic():
            stored = self._lock_stored_state()
            if stored is None:
                raise ValueError("This mail has not been saved. It cannot be sent.")
            self._sync_with_stored(stored)
            if self.sent:
                raise TypeError(
                    "This mail has been sent already. It cannot be sent again."
                )
            return self._get_recipients(pgp_config)

    def _is_delivered(self, address, member):
        if member:
            return str(member.pk) in self.delivered_to_members
        return address.lower() in {address.lower() for address in self.delivered_to}

    def _mark_sent(self):
        """Mark the mail as sent, if nobody is left to send it to.

        This is decided by the recipients and the deliveries that are stored
        now, under the lock on the mail, and not by what this object knew
        when it started to send.
        """
        with transaction.atomic():
            stored = self._lock_stored_state()
            self._sync_with_stored(stored)
            if self.sent:
                return
            if not all(
                self._is_delivered(address, member)
                for address, member in self._get_recipients()
            ):
                raise SendMailException(
                    _(
                        "The recipients of this email were changed while it "
                        "was sent. Send it again to reach the remaining "
                        "recipients."
                    )
                )
            sent = now()
            type(self)._base_manager.filter(pk=self.pk).update(sent=sent)
            self.sent = sent

    @property
    def attachment_ids(self):
        if hasattr(self, "attachments"):
            return list(self.attachments.all().values_list("pk", flat=True))
        return []

    def get_member_recipients(self):
        """The members this mail is addressed to, as a list.

        This does not use ``self.members.all()``: that goes through the
        default member manager and would leave out external contacts.
        """
        if hasattr(self, "prefetched_member_recipients"):
            return list(self.prefetched_member_recipients)
        if not self.pk:
            if self.to_type != RecipientType.MEMBER:
                return []
            return list(self._pending_member_recipients or [])
        return list(self._member_recipient_queryset())

    def _member_recipient_queryset(self):
        return Member.all_objects.filter(emails=self).order_by("pk")

    @property
    def has_deliveries(self):
        """Whether this mail reached at least one of its recipients."""
        return bool(self.delivered_to or self.delivered_to_members)

    @property
    def has_unsupported_recipient(self):
        """Whether ``to`` still holds a ``special:`` recipient of an older
        version that could not be converted and has to be reviewed."""
        return self.to_type == RecipientType.ADDRESS and self.to.startswith("special:")

    def set_member_recipients(self, members):
        """Make ``members`` the only members of this mail.

        ``self.members.set()`` is not used for the same reason as in
        ``get_member_recipients()``: it would not remove external contacts.

        The members of a mail that has been delivered to somebody are also
        the record of who received it, so they cannot be replaced anymore.
        This is decided by the stored mail, not by this object, which may
        have been loaded before a delivery took place.
        """
        members = list(members)
        with transaction.atomic():
            stored = self._lock_stored_state()
            if stored is None:
                raise ValueError("The mail has to be saved before its members are set.")
            if _has_deliveries(stored):
                raise RecipientsLockedError(
                    "The recipients of a mail cannot be changed after a delivery."
                )
            type(self).members.through.objects.filter(email=self).exclude(
                member__in=members
            ).delete()
            self.members.add(*members)
        self.__dict__.pop("prefetched_member_recipients", None)

    @property
    def recipient_display(self):
        if self.to_type == RecipientType.ALL_MEMBERS:
            return _("All members")
        if self.to_type == RecipientType.MEMBER:
            recipients = []
            for member in self.get_member_recipients():
                # the address the mail was delivered to, not the one the
                # member has today
                address = self.delivered_to_members.get(str(member.pk)) or member.email
                recipients.append(
                    f"{member.name} <{address}>" if address else str(member.name)
                )
            return ", ".join(recipients)
        if self.has_unsupported_recipient:
            return _("Review required: {to}").format(to=self.to)
        return self.to

    def _get_recipients(self, pgp_config=None):
        """Return the recipients as ``(address, member)`` pairs.

        ``member`` is only set for recipients that are addressed as members.
        The address of such a recipient is taken from the member; an address
        never leads to a member. With ``pgp_config``, the PGP keys of the
        members are loaded along with them.
        """
        if self.to_type == RecipientType.ADDRESS:
            if self.has_unsupported_recipient:
                raise SendMailException(
                    _(
                        "Cannot send this email: its recipient {to} was stored "
                        "by an older version and has to be reviewed. Select "
                        "the recipient again, or copy the mail to a new one "
                        "if it has been delivered partly."
                    ).format(to=self.to)
                )
            return [(addr.strip(), None) for addr in self.to.split(",")]

        if self.to_type == RecipientType.MEMBER:
            members = self._member_recipient_queryset()
        elif self.to_type == RecipientType.ALL_MEMBERS:
            members = (
                Member.objects.with_active_membership()
                .filter(email__isnull=False)
                .exclude(email="")
            )
        else:
            raise SendMailException(
                _("Cannot send this email: unknown recipient type {to_type}.").format(
                    to_type=self.to_type
                )
            )
        if pgp_config and pgp_config.encryption_enabled:
            members = members.prefetch_related(_active_pgp_keys_prefetch())
        recipients = [(member.email, member) for member in members]
        if not recipients and self.to_type == RecipientType.MEMBER:
            raise SendMailException(
                _("Cannot send this email: no member is set as its recipient.")
            )
        return recipients

    def send(self):
        from byro.common.models import Configuration
        from byro.mails.send import mail_send_task

        config = Configuration.get_solo()
        pgp_config = PGPConfiguration.get_solo()
        # What is sent to whom is decided by the stored mail: this object
        # takes over its recipients and deliveries first.
        recipients = self._load_stored_recipients(pgp_config)

        headers = {}
        if self.reply_to:
            headers["Reply-To"] = self.reply_to

        # Members are tracked by their identity, as several members may share
        # one address. Plain addresses are tracked by the address.
        delivered_addresses = {address.lower() for address in self.delivered_to}
        errors = []
        for addr, member in recipients:
            body = self.text
            if member:
                if str(member.pk) in self.delivered_to_members:
                    continue
                addr = (addr or "").strip()
                if not addr:
                    errors.append(
                        str(
                            _(
                                "Cannot send email to {member}: no email address."
                            ).format(member=member)
                        )
                    )
                    continue
                signature = _(
                    "You are receiving this email due to your membership in {name}."
                ).format(name=config.name)
                signature += "\n"
                signature += _(
                    "You can see your member page at this URL: {url}"
                ).format(url=member.profile_memberpage.get_url())
                body += "\n\n-- \n" + signature
            elif addr.lower() in delivered_addresses:
                continue
            try:
                mail_send_task(
                    to=[addr],
                    subject=self.subject,
                    body=body,
                    sender=config.mail_from,
                    cc=(self.cc or "").split(","),
                    bcc=(self.bcc or "").split(","),
                    attachments=self.attachment_ids,
                    headers=headers,
                    member=member,
                    pgp_config=pgp_config,
                )
            except SendMailException as e:
                errors.append(str(e))
                continue

            self._record_delivery(addr, member)

        if errors:
            raise SendMailException("\n".join(errors))

        self._mark_sent()

    def copy_to_draft(self):
        new_mail = deepcopy(self)
        new_mail.pk = None
        new_mail.sent = None
        new_mail.delivered_to = []
        new_mail.delivered_to_members = {}
        new_mail.__dict__.pop("prefetched_member_recipients", None)
        new_mail.save()
        if self.to_type == RecipientType.MEMBER:
            # only explicit member recipients are copied; the members of other
            # mails record a past delivery, not who the mail is addressed to
            new_mail.set_member_recipients(self._member_recipient_queryset())
        return new_mail


def _has_deliveries(stored):
    return bool(stored["delivered_to"] or stored["delivered_to_members"])


@receiver(m2m_changed, sender=EMail.members.through)
def protect_members_of_delivered_mails(
    sender, instance, action, reverse, pk_set, **kwargs
):
    """Refuse changes to the members of a mail that has been delivered.

    ``EMail.set_member_recipients()`` does this check on its own; this covers
    the relation itself (``mail.members`` and ``member.emails``), whatever the
    object at hand knows about the deliveries. Deliveries are recorded by
    ``EMail._record_delivery()``, which does not use the relation managers.
    """
    if action not in ("pre_add", "pre_remove", "pre_clear"):
        return
    if action == "pre_add" and not pk_set:
        return
    if not reverse:
        mails = EMail.objects.filter(pk=instance.pk)
    elif pk_set is None:
        mails = EMail.objects.filter(members=instance)
    else:
        mails = EMail.objects.filter(pk__in=pk_set)
    # the relation managers run this inside a transaction
    stored_mails = mails.select_for_update().values(*EMail.DELIVERY_FIELDS)
    if any(_has_deliveries(stored) for stored in stored_mails):
        raise RecipientsLockedError(
            "The members of a mail cannot be changed after a delivery."
        )
