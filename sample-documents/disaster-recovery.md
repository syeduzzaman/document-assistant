# Nordwerk Auto — Disaster recovery plan

This is fictional demonstration data for Document Assistant.

## Backups
Database backups run daily at 02:00 UTC and are retained for 30 days.
Backups are encrypted and stored in a separate cloud region.
The recovery point objective (RPO) is 24 hours.
The recovery time objective (RTO) is four hours.

## Recovery procedure
The on-call engineer opens an incident and selects the latest verified backup.
Restore the database into an isolated environment and validate record counts before switching traffic.
The engineering lead approves the final production switch.

## Exercises
The team performs a disaster recovery exercise every quarter.
Each exercise must record restore duration, data integrity checks and follow-up actions.
