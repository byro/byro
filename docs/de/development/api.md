# REST-API

byro hat eine REST-API für Mitglieder und Mitgliedschaften, gebaut mit
[Django REST Framework](https://www.django-rest-framework.org/) und
[drf-spectacular](https://drf-spectacular.readthedocs.io/).

## Interaktive Referenz

Die vollständige, immer aktuelle Referenz ist Teil jeder byro-Installation,
nicht dieser Seite:

* `/api/v1/docs/` – interaktive Swagger-UI mit allen Endpunkten, Parametern
  und Beispielen,
* `/api/v1/schema/` – dasselbe als OpenAPI-3-Dokument (JSON) zur
  Weiterverarbeitung, zum Beispiel um einen Client zu generieren.

Beide Seiten sind **unauthentifiziert erreichbar** – sie zeigen nur die
Struktur der API, keine Daten. Diese Seite hier beschreibt Konzepte, die im
Schema nicht von selbst auffallen.

## Authentifizierung

Die API verwendet Token-Authentifizierung: Jedes Office-Konto hat einen
eigenen Token unter „Einstellungen → API-Token“ (siehe
[Einstellungen](../administration/settings.md#api-token)), gesendet als
Header `Authorization: Token <dein-token>`. Der Token funktioniert nur,
solange das zugehörige Konto `is_staff` ist (siehe
[Benutzer und Login](../administration/users-and-login.md#benutzerkonten-verwalten));
es gibt **keine feingranularen API-Berechtigungen** – ein gültiger Token
eines `is_staff`-Kontos hat vollen Zugriff auf alle API-Endpunkte, genau wie
das zugehörige Konto vollen Zugriff auf das gesamte Office hat.

## Endpunkte

| Endpunkt | Methoden | Zweck |
|---|---|---|
| `/api/v1/members/` | GET, POST | Mitglieder auflisten (mit Filtern und Suche), anlegen |
| `/api/v1/members/<id>/` | GET, PUT, PATCH | ein Mitglied lesen, vollständig oder teilweise ändern |
| `/api/v1/members/<id>/balance/` | GET | aktuellen Saldo abfragen |
| `/api/v1/members/<id>/adjust-balance/` | POST | Saldo anpassen (Zahlung, Anfangssaldo oder Erlass, siehe unten) |
| `/api/v1/members/<id>/memberships/` | GET, POST | Mitgliedschaften eines Mitglieds auflisten, neue anlegen |
| `/api/v1/members/<id>/memberships/<id>/` | GET, PUT, PATCH, DELETE | eine Mitgliedschaft lesen, ändern, löschen |

**Es gibt keine Lösch-Methode für Mitglieder selbst** (`DELETE
/api/v1/members/<id>/` ist nicht erlaubt) – das deckt sich mit dem Office, wo
ein Mitglied ebenfalls nicht gelöscht werden kann (siehe
[Mitglieder](../usage/members.md)). Mitgliedschaften lassen sich dagegen über
die API löschen, obwohl das Office dafür keine eigene Funktion hat (dort
endest du eine Mitgliedschaft stattdessen, siehe
[Ein-/Austritt](../usage/members.md#ein-austritt)); ein Löschen über die API
entfernt den Datensatz vollständig, ohne die Historie eines Austritts.

## Filtern und Suchen

`/api/v1/members/` unterstützt Query-Parameter: `email` (exakt, ohne
Groß-/Kleinschreibung), `email__contains`, `number` (exakt), `name__contains`,
`is_active` (berechnet, siehe [Mitglieder](../usage/members.md#mitgliederliste)),
und `secret_token` (exakt – damit lässt sich ein Mitglied über den Token
seiner öffentlichen [Mitgliederseite](../usage/member-page.md) finden; wer
Zugriff auf die API hat, hat ohnehin vollen Office-Zugriff, das ist also keine
zusätzliche Rechteausweitung). Ergebnislisten sind paginiert, 50 Einträge pro
Seite.

## Saldo anpassen

`POST /api/v1/members/<id>/adjust-balance/` bildet dieselbe Kontokorrektur ab
wie der Reiter „Vorgänge“ im Office (siehe
[Saldenkorrektur](../usage/members.md#saldenkorrektur)): `amount`, optional
`memo`, `type` (`payment`, `initial` oder `waiver`) und optional
`value_datetime`. Details zu den drei Typen und ihren Kontowirkungen stehen
auf derselben Office-Referenzseite; die API bildet exakt dieselbe Logik ab.

## Architektur

Mitglieds- und Mitgliedschaftsserialisierung sind
`rest_framework.serializers.ModelSerializer`-Klassen in
`byro.api.serializers`; installierte Profil-Plugins (siehe
[Mitglieder](../usage/members.md)) erscheinen automatisch als verschachtelte
Felder unter ihrem jeweiligen Zugriffsnamen (`profile_profile`,
`profile_sepa`, …) – ein Plugin muss dafür nichts Zusätzliches tun. Die
Views leben in `byro.api.views`, die URL-Konfiguration in `byro.api.urls`.
