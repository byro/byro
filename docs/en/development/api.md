# REST API

byro has a REST API for members and memberships, built with
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
is `is_staff` (see
[Users and login](../administration/users-and-login.md#managing-user-accounts));
there are **no fine-grained API permissions** - a valid token from an
`is_staff` account has full access to every API endpoint, exactly as that
account has full access to the entire Office.

## Endpoints

| Endpoint | Methods | Purpose |
|---|---|---|
| `/api/v1/members/` | GET, POST | list members (with filters and search), create one |
| `/api/v1/members/<id>/` | GET, PUT, PATCH | read a member, change it fully or partially |
| `/api/v1/members/<id>/balance/` | GET | query the current balance |
| `/api/v1/members/<id>/adjust-balance/` | POST | adjust the balance (payment, initial balance or waiver, see below) |
| `/api/v1/members/<id>/memberships/` | GET, POST | list a member's memberships, create a new one |
| `/api/v1/members/<id>/memberships/<id>/` | GET, PUT, PATCH, DELETE | read, change, delete one membership |

**There is no delete method for members themselves** (`DELETE
/api/v1/members/<id>/` is not allowed) - matching the Office, where a member
likewise cannot be deleted (see [Members](../usage/members.md)). Memberships,
on the other hand, can be deleted through the API even though the Office has
no dedicated function for that (there you end a membership instead, see
[Joining and leaving](../usage/members.md#joining-and-leaving)); deleting
through the API removes the record completely, without the history of a
leave.

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

## Architecture

Member and membership serialization are
`rest_framework.serializers.ModelSerializer` classes in
`byro.api.serializers`; installed profile plugins (see
[Members](../usage/members.md)) automatically show up as nested fields under
their respective accessor name (`profile_profile`, `profile_sepa`, …) - a
plugin needs to do nothing extra for this. The views live in
`byro.api.views`, the URL configuration in `byro.api.urls`.
