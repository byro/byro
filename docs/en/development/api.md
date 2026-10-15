# REST API

byro has a REST API for members, memberships and member documents, built
with
[Django REST Framework](https://www.django-rest-framework.org/) and
[drf-spectacular](https://drf-spectacular.readthedocs.io/).

## Interactive reference

The complete, always up to date reference is part of every byro
installation, not this page:

* `/api/v1/docs/` - an interactive Swagger UI with every endpoint, parameter
  and example,
* `/api/v1/schema/` - the same as an OpenAPI 3 document (JSON) for further
  processing, for example to generate a client.

Both pages are **reachable without login** - they only show the API's
structure, not any data. This page covers concepts that don't stand out from
the schema by themselves.

## Authentication

The API uses token authentication: every Office account has its own token in
the user menu under *API token* (see
[My account](../usage/account.md#api-token)), sent as the header
`Authorization: Token <your-token>`. The token only works while the account
is active and staff or superuser, the same rule that decides who may sign in
to the Office (see
[Permission model](../administration/users-and-login.md#permission-model)).
A token that its owner regenerated or that a superuser revoked (see
[Managing user accounts](../administration/users-and-login.md#managing-user-accounts))
is rejected with `401` from that moment on.
There are **no fine-grained API permissions**: a valid token from such an
account has full access to every API endpoint. The API currently offers no
endpoints for the superuser-only functions (settings, user management, log).

## Endpoints

| Endpoint | Methods | Purpose |
|---|---|---|
| `/api/v1/members/` | GET, POST | list members (with filters and search), create one |
| `/api/v1/members/<id>/` | GET, PUT, PATCH | read a member, change it fully or partially |
| `/api/v1/members/<id>/balance/` | GET | query the current balance |
| `/api/v1/members/<id>/adjust-balance/` | POST | adjust the balance (payment, initial balance or waiver, see below) |
| `/api/v1/members/<id>/memberships/` | GET, POST | list a member's memberships, create a new one |
| `/api/v1/members/<id>/memberships/<id>/` | GET, PUT, PATCH, DELETE | read, change, delete one membership |
| `/api/v1/members/<id>/documents/` | GET, POST | list a member's documents, upload a new one (see below) |
| `/api/v1/members/<id>/documents/<id>/` | GET | read the metadata of one document |

**There is no delete method for members themselves** (`DELETE
/api/v1/members/<id>/` is not allowed) - matching the Office, where a member
likewise cannot be deleted (see [Members](../usage/members.md)). Memberships,
on the other hand, can be deleted through the API even though the Office has
no dedicated function for that (there you end a membership instead, see
[Joining and leaving](../usage/members.md#joining-and-leaving)); deleting
through the API removes the record completely, without the history of a
leave.

Both membership endpoints need the member from the URL. An id that belongs to
no member is answered with `404`, for every method: a member without
memberships answers `200` with an empty list, and a membership that belongs to
another member is not reachable through a member's URL. The member is looked
up after the authentication and permission checks, so `401` and `403` do not
reveal whether a member exists.

## Filtering and search

`/api/v1/members/` supports query parameters: `email` (exact, case
insensitive), `email__contains`, `number` (exact), `name__contains`,
`is_active` (computed, see [Members](../usage/members.md#member-list)), and
`secret_token` (exact - this lets you find a member via the token of their
public [member page](../usage/member-page.md); anyone with API access already
has full Office access anyway, so this is not an additional privilege
escalation). Result lists are paginated, 50 entries per page.

## Adjusting a balance

`POST /api/v1/members/<id>/adjust-balance/` maps to the same account
adjustment as the "Operations" tab in the Office (see
[Account adjustment](../usage/members.md#account-adjustment)): `amount`,
optionally `memo`, `type` (`payment`, `initial` or `waiver`) and optionally
`value_datetime`. Details on the three types and their account effects are
on the same Office reference page; the API maps exactly the same logic.

## Member documents

`/api/v1/members/<id>/documents/` lists the documents of a member and uploads
new ones, `/api/v1/members/<id>/documents/<id>/` reads a single one. These
are the documents of the "Documents" tab in the member view (see
[Documents](../usage/documents.md)).

An upload is a `POST` with `multipart/form-data`. Other content types such
as JSON are answered with `415`.

| Field | Required | Value |
|---|---|---|
| `document` | yes | the file, must not be empty |
| `title` | yes | up to 300 characters |
| `date` | no | `YYYY-MM-DD`, defaults to today |
| `category` | no | one of the installed categories (see [Categories](../usage/documents.md#categories)), defaults to `byro.documents.misc` |
| `direction` | no | `incoming`, `outgoing` or `other`, defaults to `outgoing` |

```console
$ curl -H "Authorization: Token <your-token>" \
    -F document=@application.pdf \
    -F title="Membership application" \
    -F date=2022-04-15 \
    -F category=byro.documents.registration_form \
    -F direction=incoming \
    https://byro.example.org/api/v1/members/42/documents/
```

The member comes from the URL only, and byro calculates the content hash
itself. A request that contains `member` or `content_hash` is rejected with
`400`.

The response, the list and the detail endpoint return `id`, `title`, `date`,
`category`, `direction`, `content_hash` (`sha512:` followed by the hex
digest) and `filename`. `filename` is the name byro stored the file under. It
can differ from the uploaded name, for example when a file with that name
already exists. The file itself and its storage path are not part of the
response.

Documents that were not uploaded through the API can have `null` as `title`,
`date` or `category`, and a category of a plugin that is no longer installed.
The list and the detail endpoint return them as stored. An upload accepts
neither.

An upload writes the same log entries as an upload in the Office, with the
account of the token as the user. The document and its log entries are
created together or not at all. As with an upload in the Office, a file
without a document can remain in the storage when creating the document fails
after the file was written.

What the API does not do:

* **No duplicate detection.** Uploading the same file twice creates two
  documents, as in the Office. An import that may run more than once can
  compare the `content_hash` values of the list first.
* **No download.** The file content can only be fetched in the Office (see
  [Downloading](../usage/documents.md#downloading)).
* **No changing or deleting.** `PUT`, `PATCH` and `DELETE` answer `405`.

An unknown member answers `404`, and so does a document that belongs to
another member. byro itself does not limit the size of an upload. A reverse
proxy in front of it may: nginx rejects request bodies above 1 MB unless
`client_max_body_size` says otherwise.

## Architecture

Member, membership and document serialization are
`rest_framework.serializers.ModelSerializer` classes in
`byro.api.serializers`; installed profile plugins (see
[Members](../usage/members.md)) automatically show up as nested fields under
their respective accessor name (`profile_profile`, `profile_sepa`, …) - a
plugin needs to do nothing extra for this. The views live in
`byro.api.views`, the URL configuration in `byro.api.urls`.
