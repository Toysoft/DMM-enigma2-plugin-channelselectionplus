# Changelog ChannelSelection Plus

#### 23.04.2023 - Version 0.1.0-r8:
- fix: bei Senderwechsel in der Kanalliste bei aktivem PiPzap erfolgt der Senderwechsel nun korrekt im PiP

#### 14.04.2023 - Version 0.1.0-r7:
- Kanalnummernanzeige für Ordner deaktiviert (z.B. in der Satelliten-, Anbieter- und Favoritenliste)

#### 01.04.2023 - Version 0.1.0-r6:
- bei Template-Ansichtwechsel per Spultasten wird die letzte Ansicht nun dauerhaft gespeichert
- neuer Template-Parameter "maxExtDesc" zur Begrenzung der Zeichenanzahl bei Nutzung von text=26 in den Templates(für bessere Navigations-Performance in der Kanalliste bei langen extDesc-Texten)
- Unterstützung für svg's als ServiceType-Icons im Skinpfad
- verbesserte Navigations-Performance, wenn im aktuellen Template keine EventImages verwendet werden (wenn im Template png=40 nicht verwendet wird)

#### 17.10.2022 - Version 0.1.0-r4:
- fix für fehlerhafte Anzeige nach Ansichtwechsel im ValisEPG
- Kanalnummern-Anzeige-Setup-Option greift jetzt auch bei den Template-Kanalnamen-Texten (text=1, text=36, text=41)
- neue Setup-Option für das Verhalten der Info-Taste im TV-Modus (Einfach-EPG oder EventView)
- neue Setup-Option "Zeige DVB-Icons" (Icon ist in Templates unabhängig von dieser Option immer über png=3 verfügbar)
- es wird jetzt auch das Streaming-Icon aus dem Skin (ico_streaming-fs8.png) für die DVB-Icons unterstützt

#### 30.07.2022 - Version 0.1.0-r3:
- fix für fehlerhafte ProgressBarPixmap-Breite in der Standard-Ansicht nach Ansichtwechsel

#### 20.02.2022 - Version 0.1.0-r2:
- fix für fehlerhaftes backgroundPixmap in der Standard-Ansicht
- fix für falsche Setup-Optionen-Ansicht nach Wechsel der Kanallisten-Ansicht in der Vorschau

#### 22.01.2022 - Version 0.1.0-r1:
- direkter Wechsel zwischen allen Ansichten (Standard und Template-Ansichten) mit den Spultasten (ohne vorherige Umschaltung der Kanallisten-Darstellung Standard <-> Template im Setup)
- Support für das EventDataManager-Plugin - Anzeige von Event-Images anstelle der picons (png=40)
- neuer Text-Wert "ServicenameEventName" (text=41)
- Sprachfile für italienisch (Thanks to Spaeleus)

#### 28.07.2021 - Version 0.0.9-r9:
- neuer Text-Wert "ChannelnumberServicename" (text=36)
- neuer Text-Wert "ProviderName" (text=38)
- Support für "ProviderPicon" (png=39)
- optimierter Text für eventName_fullDescription (text=26) 
- neues Picture picInBouquet (png=37) - nur im Merlin-Image
- Übersetzung für Texte bei fehlenden EPG-Infos zu primetimeEvents und moreNextEvents

#### 27.06.2021 - Version 0.0.9-r8:
- fix für fehlerhafte Template-Auswahl im Setup
- fix für die Anzeige der Eventlisten für PrimetimeEvents und NextEvents

#### 26.06.2021 - Version 0.0.9-r7:
- optionales default-picon speziell für das ChannelSelectionPlus-Plugin (picon_default_csp.png im Skin-Pfad)
- Template-Wechsel mit "<<" und ">>" jetzt direkt in der Kanalliste möglich (bisher nur in der Vorschau)
- Optimierung der Template-Funktion "MultiContentTemplateColor", so dass dort jetzt auch ein Farbname mitgegeben werden kann
- der 2. übergebene Wert in den Template-Optionen für den scrollbarMode wird jetzt vom Plugin gesetzt
- neue Textwerte primetimeEventName (text=31), primetimeEventTime (text=32) und primetimeHeading (text=35)
- neue Template-Optionen "moreNextEvents":(x,w) (text=33) und "primetimeEvents":(x,w) (text=34) 

#### 22.06.2021 - Version 0.0.9-r6:
- 3 neue Textwerte zur optimierten Anzeige in der Kanalliste
* nextEventName_text  # text=28 (hier wird nur der nextEventName angezeigt, bei text=21 wird Zeit+Name angezeigt)
* nextEventTime_text  # text=29 for example '14.30 - 15.30'
* nowEventTime_text   # text=30 for example '12.00 - 14.30'

#### 20.06.2021 - Version 0.0.9-r5
- Template-Funktion für die Kanalliste (im Kanallisten-Setup aktivierbar)
- Kanallisten-Vorschau-Funktion im Kanallisten-Setup per Info-Taste (so können geänderte Einstellungen sofort angezeigt werden, ohne das Setup zu verlassen)
- neue Option zum Auswählen des letzten Kanals (lt. Kanal-History) beim Bouquet-Wechsel
- im Template-Modus wird das Default-Picon angezeigt, wenn kein passendes Picon gefunden wurde
- um teilweise leere Kanallisten zu vermeiden, wird jetzt bei nicht vorhandenen EPG-Daten in der Kanalliste bei den Event-Feldern ein default-Text 'keine Sendungsinfo' bzw. 'no event data' angezeigt

#### 27.03.2021 - Version 0.0.8
- neue Setup-Option für das Verhalten der OK-Taste (zap+close oder 1.zap und 2. close)
- fix für die Anzeige der PrimeTime im ValisEPG wenn als 2. Zeile die kommende Sendung aktiviert ist

#### Version 0.0.7
- Fix aus Version 0.5 (Position für Zusatzinfo) wird jetzt nur noch angewendet, wenn die Sendungsinfo unter dem Kanalnamen angezeigt wird
- Fix für Anzeige im Verschiebe-Modus (da haben sich in einigen Skins die Texte der 1. und 2. Zeile gegenseitig überlagert/verdeckt)
- Fix für Anzeige der Zusatzanzeige (bei Zusatzanzeige voraus, Sendungsinfo unter Kanalname und Progressbar hinter Sendername)
  (dazu wurde auch im Setup die Option 'nach Sendername' in der Progress-Position entfernt, wenn Sendungsinfo unter Kanalname steht)
- Unterstützung für ValisEPG ab Version 1.6r5 zur Anzeige der PrimeTime-Sendungen direkt in der Kanalliste (inkl. Timer-Symbole)

#### Version 0.0.6
- im Merlin-Image wurde der Aufruf der Kanallisten-Einstellungen aus dem Hauptmenü (Merlin-Untermenü in Einstellungen) angepasst
  (bisher öffnete sich dort noch die Original-Kanallisteneinstellung - also ohne die Anpassungen der ChannelSelectionPlus)

#### Version 0.0.5
- Position für Zusatzinfo korrigiert (bei Option voraus), wenn dahinter noch der Sendungsfortschritt angezeigt wird

#### Version 0.0.4
- Audio-Taste zum Suchen mit EPGSearch wieder in die EPG-Listen integriert (Funktionialität wurde zuletzt aus dem EPGSearch entfernt)

#### Version 0.0.3
- Pluginname in ChannelSelectionPlus geändert
- Fehler in den Kanallisteneinstellungen behoben (es wurde beim Öffnen der Einstellungen bei Zusatzinfo immer auf 'Prozent' zurückgesetzt)
- Übersetzung für die neuen Optionen in den Kanallisteneinstellungen (bisher nur englische Texte)

#### Version 0.0.2
- Versionsnummernanzeige in den Kanallisteneinstellungen
- Ausblenden der Merlin-Option 'Kanalnummern-Ausrichtung' wenn 'Kanalnummern-Position' = 'zusammen mit Kanalname'