# REST-API

byro hat eine REST-API für Mitglieder, Mitgliedschaften und Dokumente von
Mitgliedern, gebaut mit
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
eigenen Token im Benutzermenü unter *API-Token* (siehe
[Mein Konto](../usage/account.md#api-token)), gesendet als
Header `Authorization: Token <dein-token>`. Der Token funktioniert nur,
solange das zugehörige Konto aktiv und Staff oder Superuser ist; dieselbe
Regel entscheidet, wer sich am Office anmelden darf (siehe
[Berechtigungsmodell](../administration/users-and-login.md#berechtigungsmodell)).
Ein Token, den sein Konto erneuert oder den ein Superuser widerrufen hat
(siehe
[Benutzerkonten verwalten](../administration/users-and-login.md#benutzerkonten-verwalten)),
wird von diesem Moment an mit `401` abgelehnt.
Es gibt **keine feingranularen API-Berechtigungen**: Ein gültiger Token eines
solchen Kontos hat vollen Zugriff auf alle API-Endpunkte. Für die Funktionen,
die nur Superusern offenstehen (Einstellungen, Benutzerverwaltung, Log),
bietet die API derzeit keine Endpunkte.

## Endpunkte

| Endpunkt | Methoden | Zweck |
|---|---|---|
| `/api/v1/members/` | GET, POST | Mitglieder auflisten (mit Filtern und Suche), anlegen |
| `/api/v1/members/<id>/` | GET, PUT, PATCH | ein Mitglied lesen, vollständig oder teilweise ändern |
| `/api/v1/members/<id>/balance/` | GET | aktuellen Saldo abfragen |
| `/api/v1/members/<id>/adjust-balance/` | POST | Saldo anpassen (Zahlung, Anfangssaldo oder Erlass, siehe unten) |
| `/api/v1/members/<id>/memberships/` | GET, POST | Mitgliedschaften eines Mitglieds auflisten, neue anlegen |
| `/api/v1/members/<id>/memberships/<id>/` | GET, PUT, PATCH, DELETE | eine Mitgliedschaft lesen, ändern, löschen |
| `/api/v1/members/<id>/documents/` | GET, POST | Dokumente eines Mitglieds auflisten, ein neues hochladen (siehe unten) |
| `/api/v1/members/<id>/documents/<id>/` | GET | die Metadaten eines Dokuments lesen |

**Es gibt keine Lösch-Methode für Mitglieder selbst** (`DELETE
/api/v1/members/<id>/` ist nicht erlaubt) – das deckt sich mit dem Office, wo
ein Mitglied ebenfalls nicht gelöscht werden kann (siehe
[Mitglieder](../usage/members.md)). Mitgliedschaften lassen sich dagegen über
die API löschen, obwohl das Office dafür keine eigene Funktion hat (dort
endest du eine Mitgliedschaft stattdessen, siehe
[Ein-/Austritt](../usage/members.md#ein-austritt)); ein Löschen über die API
entfernt den Datensatz vollständig, ohne die Historie eines Austritts.

Beide Mitgliedschafts-Endpunkte brauchen das Mitglied aus der URL. Eine ID,
die zu keinem Mitglied gehört, wird mit `404` beantwortet, und zwar für jede
Methode: ein Mitglied ohne Mitgliedschaften wird mit `200` und einer leeren
Liste beantwortet, und eine Mitgliedschaft, die zu einem anderen Mitglied
gehört, ist über die URL eines Mitglieds nicht erreichbar. Das Mitglied wird
nach den Authentifizierungs- und Berechtigungsprüfungen nachgeschlagen, damit
`401` und `403` nicht verraten, ob ein Mitglied existiert.

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

## Dokumente eines Mitglieds

`/api/v1/members/<id>/documents/` listet die Dokumente eines Mitglieds auf
und lädt neue hoch, `/api/v1/members/<id>/documents/<id>/` liest ein
einzelnes. Es sind die Dokumente aus dem Reiter „Dokumente“ der
Mitgliedsansicht (siehe [Dokumente](../usage/documents.md)).

Ein Upload ist ein `POST` mit `multipart/form-data`. Andere Content-Types wie
JSON werden mit `415` beantwortet.

| Feld | Pflicht | Wert |
|---|---|---|
| `document` | ja | die Datei, darf nicht leer sein |
| `title` | ja | bis zu 300 Zeichen |
| `date` | nein | `JJJJ-MM-TT`, Standard ist das heutige Datum |
| `category` | nein | eine der installierten Kategorien (siehe [Kategorien](../usage/documents.md#kategorien)), Standard ist `byro.documents.misc` |
| `direction` | nein | `incoming`, `outgoing` oder `other`, Standard ist `outgoing` |

```console
$ curl -H "Authorization: Token <dein-token>" \
    -F document=@antrag.pdf \
    -F title="Mitgliedsantrag" \
    -F date=2022-04-15 \
    -F category=byro.documents.registration_form \
    -F direction=incoming \
    https://byro.example.org/api/v1/members/42/documents/
```

Das Mitglied ergibt sich ausschließlich aus der URL, und den Content-Hash
berechnet byro selbst. Ein Request, der `member` oder `content_hash` enthält,
wird mit `400` abgewiesen.

Die Antwort, die Liste und der Einzelabruf liefern `id`, `title`, `date`,
`category`, `direction`, `content_hash` (`sha512:` gefolgt vom Hex-Digest)
und `filename`. `filename` ist der Name, unter dem byro die Datei gespeichert
hat. Er kann vom hochgeladenen Namen abweichen, zum Beispiel wenn es schon
eine Datei mit diesem Namen gibt. Die Datei selbst und ihr Speicherpfad sind
nicht Teil der Antwort.

Dokumente, die nicht über die API hochgeladen wurden, können bei `title`,
`date` oder `category` den Wert `null` haben oder eine Kategorie eines
Plugins, das nicht mehr installiert ist. Liste und Einzelabruf geben sie so
aus, wie sie gespeichert sind. Ein Upload nimmt beides nicht an.

Ein Upload schreibt dieselben Log-Einträge wie ein Upload im Office, mit dem
Konto des Tokens als Benutzer. Das Dokument und seine Log-Einträge entstehen
gemeinsam oder gar nicht. Wie bei einem Upload im Office kann eine Datei ohne
Dokument im Storage zurückbleiben, wenn das Anlegen scheitert, nachdem die
Datei geschrieben wurde.

Was die API nicht tut:

* **Keine Duplikaterkennung.** Dieselbe Datei zweimal hochzuladen ergibt zwei
  Dokumente, wie im Office. Ein Import, der mehrfach laufen kann, vergleicht
  vorher die `content_hash`-Werte der Liste.
* **Kein Download.** Den Dateiinhalt gibt es nur im Office (siehe
  [Herunterladen](../usage/documents.md#herunterladen)).
* **Kein Ändern oder Löschen.** `PUT`, `PATCH` und `DELETE` werden mit `405`
  beantwortet.

Ein unbekanntes Mitglied wird mit `404` beantwortet, ebenso ein Dokument, das
zu einem anderen Mitglied gehört. byro selbst begrenzt die Größe eines
Uploads nicht. Ein vorgeschalteter Reverse Proxy kann das tun: nginx weist
Request-Bodys über 1 MB ab, solange `client_max_body_size` nichts anderes
festlegt.

## Architektur

Die Serializer für Mitglieder, Mitgliedschaften und Dokumente sind
`rest_framework.serializers.ModelSerializer`-Klassen in
`byro.api.serializers`; installierte Profil-Plugins (siehe
[Mitglieder](../usage/members.md)) erscheinen automatisch als verschachtelte
Felder unter ihrem jeweiligen Zugriffsnamen (`profile_profile`,
`profile_sepa`, …) – ein Plugin muss dafür nichts Zusätzliches tun. Die
Views leben in `byro.api.views`, die URL-Konfiguration in `byro.api.urls`.
