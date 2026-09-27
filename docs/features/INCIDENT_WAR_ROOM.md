# Incident War Room

## The problem it solves

An incident was a group of linked appeals. An operator needs it to be the
operational record of one city problem: who reported it, where the reports fall,
who owns it, what was done about comparable problems, what the evidence says and
what can be done next.

## One read

`GET /v1/incidents/{id}/workspace` assembles everything inside one connection.
The frontend used to need a request per panel, which is slow and invites panels
to disagree with each other, because each one sees a different instant.

The endpoint is read-only by construction. Every write stays on its own domain
endpoint, so the war room cannot become a side door around the human decision
path.

## Sections

- **Situation**: members, confirmed and candidate counts, how long it has been
  active, topic and service.
- **Report footprint**: the reports on a map, their centroid and spread.
- **Ownership**: candidates from the existing resolver, with the rules that
  matched and any loop risk.
- **Comparable verified outcomes**: from outcome memory, human-closed only.
- **Next actions**: rule-based suggestions with their reason codes.
- **Delivery**: queued, delivered, retrying and permanently failed.
- **Timeline and evidence**: append-only events and attached artefacts.

## The map says footprint, not impact

The radius describes the spread of the reports this incident received. Calling
it an impact area would assert something about people who never reported
anything. The UI text says so next to the figure.

There is no tile layer and no mapping library. A tile request would send the
location of citizen reports to a third party every time somebody opened an
incident. The projection is equirectangular with a cosine correction on
longitude, which is accurate over the few kilometres an incident covers.

## Absent geography is the normal case

No regional export in this programme carries coordinates. The footprint reports
`unavailable, COORDINATES_ABSENT` rather than drawing an empty canvas, and a
single located report abstains, because spread across one point means nothing.
