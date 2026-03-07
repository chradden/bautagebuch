# Bautagebuch – Bedienungsanleitung

## Willkommen

Das Bautagebuch ist eine Kombination aus Telegram-Bot und Web-Dashboard. Sie erfassen Baustellen- oder Instandhaltungsinformationen direkt per Smartphone und erhalten daraus strukturierte Einträge, PDF-Berichte und CSV-Exporte.

Die App ist für den einfachen Einsatz im Alltag gedacht:

- Meldung per Text senden
- Fotos zur Dokumentation hochladen
- Befunde per Sprachnachricht diktieren
- Projektadresse per Standortfreigabe hinterlegen
- Tagesberichte als PDF erzeugen
- Einträge und Berichte im Web-Dashboard verwalten

---

## Inhaltsverzeichnis

1. [Was Sie brauchen](#1-was-sie-brauchen)
2. [Erste Schritte und Registrierung](#2-erste-schritte-und-registrierung)
3. [Ihr erstes Projekt anlegen](#3-ihr-erstes-projekt-anlegen)
4. [Adresse per Standort setzen](#4-adresse-per-standort-setzen)
5. [Meldungen erfassen](#5-meldungen-erfassen)
6. [KI-Priorisierung und Kostenschätzung](#6-ki-priorisierung-und-kostenschaetzung)
7. [Projekt wechseln und Status prüfen](#7-projekt-wechseln-und-status-pruefen)
8. [Berichte und Exporte](#8-berichte-und-exporte)
9. [Das Web-Dashboard](#9-das-web-dashboard)
10. [Tägliche Erinnerung](#10-taegliche-erinnerung)
11. [Tipps für die Praxis](#11-tipps-fuer-die-praxis)
12. [Befehlsübersicht](#12-befehlsuebersicht)
13. [Häufige Fragen](#13-haeufige-fragen)

---

## 1. Was Sie brauchen

- Telegram auf dem Smartphone
- Den Link oder Namen des Bots
- Das Bot-Passwort, falls der Zugang geschützt ist
- Optional die Zugangsdaten für das Web-Dashboard

Sie brauchen keine zusätzliche App. Die Erfassung läuft direkt über Telegram.

---

## 2. Erste Schritte und Registrierung

### So starten Sie:

1. Öffnen Sie den Bot in Telegram.
2. Tippen Sie auf Start oder senden Sie:

```text
/start
```

3. Falls ein Passwortschutz aktiv ist, fordert der Bot zuerst das Zugangspasswort an.
4. Danach geben Sie Ihren Namen ein.
5. Anschließend ist Ihr Benutzerkonto angelegt.

### Wichtig zum Passwortschutz

- Wenn ein Passwort eingerichtet ist, wird Ihre Passwort-Nachricht nach Möglichkeit direkt aus dem Chat gelöscht.
- Nach drei falschen Versuchen beendet der Bot den Vorgang und verweist auf den Administrator.

### Namen später ändern

Falls Ihr Name in Berichten angepasst werden soll, senden Sie:

```text
/name Vorname Nachname
```

Beispiel:

```text
/name Max Mustermann
```

---

## 3. Ihr erstes Projekt anlegen

Bevor Sie Meldungen erfassen, legen Sie ein Projekt beziehungsweise Objekt an. Alle Einträge werden immer dem aktuell aktiven Projekt zugeordnet.

### Befehl:

```text
/projekt Neubau Rathaus
```

Der Bot legt das Projekt an und aktiviert es sofort.

### Geeignete Projektnamen

- Neubau Rathaus
- Wohnanlage Gartenweg 12
- Kita Nordflügel
- Bürogebäude Schönhauser Allee 45

Nach der Anlage können Sie direkt loslegen und Text, Fotos oder Sprachnachrichten senden.

---

## 4. Adresse per Standort setzen

Sie können die Projektadresse automatisch aus Ihrem Standort übernehmen lassen. Das ist besonders praktisch, wenn Sie direkt vor Ort sind.

### Schrittfolge:

1. Aktivieren Sie zuerst das gewünschte Projekt.
2. Senden Sie den Befehl:

```text
/standort
```

3. Telegram zeigt eine Schaltfläche zum Teilen Ihres Standorts.
4. Senden Sie Ihren Standort.
5. Der Bot übernimmt daraus die Adresse und speichert zusätzlich die Koordinaten.

Die Adresse wird später in Berichten und im Dashboard angezeigt.

---

## 5. Meldungen erfassen

Die App kennt drei praktische Wege für Einträge:

- Textnachrichten
- Fotos
- Sprachnachrichten

### 5.1 Textnachrichten

Jede normale Textnachricht wird als Bautagebuch-Eintrag gespeichert und durch die KI ausgewertet.

Beispiele:

```text
Rissbildung an der Nordfassade im Bereich Fensterband 2. Obergeschoss.
```

```text
Heizung im Technikraum ausgefallen, Vorlauf kalt, Ursache noch unklar.
```

```text
Regenrinne an Halle B teilweise gelöst, Absturzgefahr fuer lose Teile.
```

Der Bot antwortet mit Kategorie, Priorität und gegebenenfalls einer Kostenschätzung.

### 5.2 Fotos senden

Sie können ein Foto direkt an den Bot schicken. Optional können Sie eine Bildbeschreibung als Text dazuschreiben.

Typischer Ablauf:

1. Foto in Telegram aufnehmen oder aus der Galerie auswählen.
2. Optional einen kurzen Begleittext ergänzen.
3. Senden.

Der Bot speichert das Foto projektbezogen und erzeugt zusätzlich eine KI-Beschreibung zum Bildinhalt.

### 5.3 Sprachnachrichten

Wenn Sie unterwegs sind oder keine Hand frei haben, können Sie Befunde auch einfach einsprechen.

Beispiel:

"Im Keller West steht Wasser, vermutlich kommt es aus dem Bereich der Hebeanlage. Bitte dringend prüfen."

Die App transkribiert die Nachricht automatisch, speichert den Text als Eintrag und bewertet ihn wie eine normale Textmeldung.

---

## 6. KI-Priorisierung und Kostenschätzung

Die App bewertet Meldungen automatisch nach Dringlichkeit. Dadurch sehen Sie sofort, was zuerst bearbeitet werden sollte.

### Prioritäten

| Priorität | Bedeutung | Typische Fälle |
|---|---|---|
| Rot | Sofort handeln | Sicherheitsrisiko, Havarie, akute Ausfälle |
| Gelb | Zeitnah beheben | Funktionsstörung, Schaden mit Folgerisiko |
| Grün | Planbar | kleinere Mängel, Wartung, unkritische Punkte |

### Kategorien

Die KI ordnet Meldungen zusätzlich einer Kategorie zu, zum Beispiel:

- Reparatur
- Mängelbeseitigung
- Wartung
- Prüfung
- Sicherheit
- Sonstiges

### Kostenschätzung

Wenn die Beschreibung ausreichend klar ist, ergänzt der Bot eine grobe Kostenschätzung. Diese hilft bei der Priorisierung und erscheint auch in den Berichten.

---

## 7. Projekt wechseln und Status prüfen

### Aktives Projekt wechseln

Wenn Sie für mehrere Baustellen oder Objekte arbeiten, können Sie das aktive Projekt wechseln:

```text
/wechsel
```

Der Bot zeigt dann eine Auswahlliste mit vorhandenen Projekten. Nach der Auswahl werden alle weiteren Meldungen diesem Projekt zugeordnet.

### Tagesstatus anzeigen

Mit diesem Befehl sehen Sie Ihr aktives Projekt und wie viele Meldungen heute erfasst wurden:

```text
/status
```

Angezeigt werden:

- aktives Objekt
- aktuelles Datum
- Anzahl Textmeldungen
- Anzahl Fotos
- Anzahl Sprachnachrichten
- Gesamtzahl der heutigen Einträge

---

## 8. Berichte und Exporte

### 8.1 PDF-Bericht im Bot erstellen

Für das aktuell aktive Projekt können Sie jederzeit einen Tagesbericht erzeugen.

Für heute:

```text
/bericht
```

Für ein bestimmtes Datum:

```text
/bericht 07.03.2026
```

Voraussetzung ist, dass für diesen Tag bereits Einträge vorhanden sind.

Der erzeugte Bericht wird als PDF in den Chat gesendet.

### Was im PDF-Bericht enthalten ist

- Projektname
- Datum
- verantwortlicher Benutzer
- Projektadresse, falls hinterlegt
- Einträge des Tages in zeitlicher Reihenfolge
- KI-Zusammenfassung
- Prioritäten und Kostenschätzungen
- Fotodokumentation

### 8.2 CSV-Export im Bot

Alle Einträge können Sie zusätzlich als CSV-Datei exportieren.

Kompletter Export des aktiven Projekts:

```text
/export
```

Export für einen bestimmten Tag:

```text
/export 07.03.2026
```

Der Export eignet sich gut für Excel, Auswertungen oder die Weitergabe an andere Systeme.

---

## 9. Das Web-Dashboard

Neben dem Bot gibt es ein Web-Dashboard. Standardmäßig läuft es unter:

```text
http://localhost:8093
```

Im Betrieb auf einem Server wird statt localhost die jeweilige Server-Adresse oder Domain verwendet.

### Anmeldung

- Wenn ein Dashboard-Passwort gesetzt ist, melden Sie sich mit Benutzername und Passwort an.
- Wenn kein Passwort gesetzt ist, öffnet sich das Dashboard direkt.

### 9.1 Startseite

Auf der Startseite sehen Sie alle Projekte als Kartenansicht mit:

- Adresse
- Anzahl Meldungen
- Anzahl Fotos
- Anzahl Berichte
- letzte Einträge

### 9.2 Projekte in Ordner organisieren

Projekte können im Dashboard in Ordner verschoben werden. Dadurch lassen sich größere Bestände sauber strukturieren, zum Beispiel nach Region, Auftraggeber oder Objektart.

Möglich sind:

- Projekt in vorhandenen Ordner verschieben
- neuen Ordner anlegen
- Ordner umbenennen
- Ordner auflösen

### 9.3 Projekt-Detailseite

Auf der Projektseite stehen zwei Bereiche zur Verfügung:

- Meldungen
- Berichte

Im Bereich Meldungen können Sie:

- alle Einträge sehen
- nach Datum filtern
- nach Kategorie filtern
- Fotos direkt ansehen
- KI-Zusammenfassungen lesen

Im Bereich Berichte können Sie:

- einen neuen Bericht für ein vorhandenes Datum erzeugen
- bereits erzeugte PDFs herunterladen

### 9.4 CSV-Export im Dashboard

Auch im Dashboard steht ein CSV-Export zur Verfügung. Wenn ein Datumsfilter aktiv ist, bezieht sich der Export auf genau diesen Zeitraum.

### 9.5 Projekte löschen

Ein Projekt kann im Dashboard vollständig gelöscht werden. Dabei werden auch die zugehörigen Einträge, Fotos und PDF-Berichte entfernt.

Zur Sicherheit müssen Sie den Projektnamen vor dem Löschen exakt bestätigen.

---

## 10. Tägliche Erinnerung

Die App versendet täglich um 18:00 Uhr eine Erinnerung an Benutzer mit aktivem Projekt.

- Wenn an diesem Tag schon Meldungen erfasst wurden, erinnert der Bot an die Erstellung des Tagesberichts.
- Wenn noch keine Meldungen vorhanden sind, erinnert der Bot an die Dokumentation.

So geht die tägliche Berichterstellung im Alltag nicht unter.

---

## 11. Tipps für die Praxis

### Für gute Textmeldungen

- Schaden oder Beobachtung konkret beschreiben
- Ort im Objekt angeben
- wenn möglich Ursache oder Auswirkung nennen
- kurz und präzise formulieren

Beispiel:

Statt:

```text
Fenster defekt.
```

Besser:

```text
Fenster im Besprechungsraum 2.12 schließt nicht mehr sauber, Zugluft deutlich spuerbar.
```

### Für gute Fotos

- Schaden möglichst nah und scharf aufnehmen
- bei Bedarf zusätzlich ein Übersichtsbild senden
- bei mehreren Schäden lieber mehrere Fotos nacheinander schicken
- einen kurzen Begleittext ergänzen, wenn der Kontext wichtig ist

### Für Sprachnachrichten

- langsam und klar sprechen
- Standort und Problem direkt benennen
- lieber eine präzise Nachricht als mehrere unklare Nachträge

---

## 12. Befehlsübersicht

| Befehl | Funktion |
|---|---|
| /start | Registrierung starten |
| /name Name | eigenen Namen ändern |
| /projekt Name | neues Projekt anlegen und aktivieren |
| /wechsel | aktives Projekt wechseln |
| /standort | Adresse per Standortfreigabe setzen |
| /status | Tagesstatus des aktiven Projekts anzeigen |
| /bericht | PDF-Bericht für heute erzeugen |
| /bericht TT.MM.JJJJ | PDF-Bericht für ein bestimmtes Datum erzeugen |
| /export | CSV-Export für das aktive Projekt |
| /export TT.MM.JJJJ | CSV-Export für ein bestimmtes Datum |
| /hilfe | Befehlsübersicht im Bot anzeigen |

---

## 13. Häufige Fragen

### Ich sende eine Meldung, aber der Bot speichert nichts.

Prüfen Sie zuerst, ob Sie registriert sind und ein aktives Projekt gesetzt haben. Nutzen Sie dazu /start und /status.

### Warum kann ich keinen Bericht erstellen?

Ein PDF-Bericht kann nur erzeugt werden, wenn für das gewählte Datum bereits Einträge vorhanden sind.

### Muss ich Fotos immer mit Text ergänzen?

Nein. Ein Foto kann auch ohne Begleittext gesendet werden. Mit einem kurzen Zusatztext wird die Einordnung aber oft besser.

### Kann ich mehrere Projekte gleichzeitig verwalten?

Ja. Sie wechseln einfach mit /wechsel zwischen den Projekten.

### Wer sieht das Dashboard?

Wenn ein Dashboard-Passwort gesetzt ist, nur Benutzer mit diesen Zugangsdaten. Ohne Passwortschutz ist das Dashboard offen erreichbar.

### Kann ich ein Projekt versehentlich löschen?

Nur im Dashboard und erst nach ausdrücklicher Namensbestätigung. Das reduziert versehentliche Löschungen deutlich.

---

## Kurz gesagt

Der einfachste Arbeitsablauf ist meistens dieser:

1. Mit /start anmelden.
2. Mit /projekt ein Objekt aktivieren.
3. Meldungen per Text, Foto oder Sprache senden.
4. Optional mit /standort die Adresse hinterlegen.
5. Mit /bericht den Tagesbericht erzeugen.
6. Im Dashboard Berichte, Fotos und Exporte verwalten.

Damit haben Sie eine vollständige, alltagstaugliche Dokumentation direkt aus Telegram heraus.