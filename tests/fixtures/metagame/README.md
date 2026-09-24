# Metagame fixtures (F173)

Fixtures for the metagame source adapters. **Tests never hit the network.**

> **Synthetic fixtures — revalidate on the first real collection.**
> Captured on 2026-09-24 from the cloud sandbox, where the egress proxy refused
> every request to the source hosts (`CONNECT tunnel failed, response 403` for
> curl; "proxy refused the connection" for WebFetch). They were written by hand
> from the publicly documented page/JSON structure. See ADR-0016 § "Live
> verification: pending-user".

| Folder | Source | Used by |
|---|---|---|
| `edhrec/` | EDHREC JSON (Commander) | F173-T07 `EdhrecSource` |
| `mtgtop8/` | MTGTop8 HTML + MTGO text export (constructed) | F173-T08 `Mtgtop8Source` |
