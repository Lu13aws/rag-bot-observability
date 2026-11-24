# CLAUDE.md

## Projekt
rag-bot-observability: Requirements-first KPI monitoring for a RAG
assistant on AWS (S3, Glue, Athena, QuickSight). Portfolio-Projekt,
öffentliches Repo, Autor: Luciano Sulaimon.

## Ziel
Zeigen, wie aus Business-Anforderungen KPIs, Datenmodell und
QuickSight-Dashboards entstehen. Requirements stehen vor der Technik.

## Struktur
- docs/: Requirements, KPI-Katalog, Datenmodell, Architektur, UAT, Governance
- ingestion/, glue/, sql/, quicksight/, sample-data/, infra/

## Arbeitsregeln
- Sprache: Doku und Code-Kommentare auf Englisch, Chat mit mir auf Deutsch.
- Ich baue selbst und muss alles im Interview erklären können:
  erkläre Änderungen kurz, baue nichts ungefragt um.
- Nichts erfinden: Doku darf nur beschreiben, was wirklich umgesetzt ist.
  Die Roadmap in der README ehrlich pflegen.
- Öffentliches Repo: keine Secrets (AWS-Keys, .env, Account-IDs), keine
  echten Nutzerdaten, nur synthetische Daten, nichts aus meiner Jobsuche.
- Vor jedem Commit prüfen, dass keine Zugangsdaten enthalten sind.
- Kosten klein halten (Budgetlimit [50 USD/Monat]), Ressourcen nach
  Tests wieder löschen.

## Konventionen
- Parquet/Snappy, Hive-Partitionierung nach Datum
- KPIs nur über den KPI-Katalog definieren (docs/02-kpi-katalog.md)
- Commit-Messages kurz, im Imperativ, Englisch