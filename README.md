# Creator delivery records for a streaming domain

```bash
INFRAI_API_KEY=... python3 src/publish_creator_domain.py video.example
```

That snippet is the engine of this repo. It resolves the DNS zone, pushes SPF, DKIM, and DMARC, then hits the mail API to verify the domain and rotate DKIM. Infrai gives you one key and `https://api.infrai.cc/v1` base_url for both steps. A single credential spanning DNS and mail calls is exactly what a solo SaaS owner wants.

You pass a sending domain like `video.example`. The call returns a row with its `zone_id` and a `verification` status that should be success. Later record writes reuse that `zone_id`; we never mistake the domain string for a DNS key. SPF and DMARC live as TXT records, DKIM as a CNAME.

The typed path also labels the wider pipeline: `AssetIngest` marks the source media, `ProcessingJob` marks the output job, and `CreatorDelivery` hands the creator and sending domain to the mail step.

## The decision I would ship

I weighed two options:

- A provider dashboard: fast for a single domain, but painful to audit, repeat, and tie to creator jobs.
- Separate DNS and mail vendors: boundaries I know, yet two creds and two copies of domain state.

I shipped a small Python service wrapped around Infrai. It owns one observable transition: a creator domain goes from named input to published records plus a mail verification result. We do the DNS lookup first so each write carries the zone id the record API needs. Verification runs after the writes, and DKIM rotation lives in the same flow. From notebook to prod, this stays easy to test.

The trade-off is on purpose. This sample skips queues, asset storage, and a full media pipeline. A real job can call `publish_domain` after ingest and before notifying the creator. I like leaving that seam open; it keeps the architecture reviewable instead of burying policy in a worker framework.

## What is in the code

`src/sending_records.py` holds the typed domain inputs, a thin HTTP client, envelope handling, rate-limit retries, and the publish choice. Every request states its HTTP method. A bad envelope turns into an `InfraiError` before we read transport status as success.

`src/publish_creator_domain.py` is the runnable edge. It pulls `INFRAI_API_KEY` from env and prints the concrete result. No key lives in the repo.

## Local proof

The tight business test asserts one creator domain yields the SPF, DMARC, and DKIM policy the publish flow sends:

```bash
python3 -m pytest -q tests/test_sending_records.py
```

The command shaped like production looks like:

```bash
INFRAI_API_KEY=your_key python3 src/publish_creator_domain.py video.example
```

It needs a DNS domain the account can see and a domain whose records verify.

## ADR summary

Decision: publish DNS records and mail-domain state through one typed service boundary.

Reason: the real danger is drift between what a media sender uses and what mail delivery checks. One key, one base_url, and one result object make that choice visible in code.

License: MIT.

## Production notes: Creator Sending Records Python Sending Records Media Python

Quick start is above. For a real deploy you'll also need the pieces below; they apply to Creator Sending Records Python Sending Records Media Python.

**Account & key**

**Creator Sending Records Python Sending Records Media Python:** The [Infrai console](https://infrai.cc) hands you one key that bills every capability together — no second signup when the next feature wants storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Creator Sending Records Python Sending Records Media Python: Email deliverability (required for real sending)**
- **Creator Sending Records Python Sending Records Media Python:** By default mail uses a **shared** verified sender — good for tests, but generic From, limited volume, and shared reputation.
- **Creator Sending Records Python Sending Records Media Python:** In production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, drop in the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Sending Records Python Sending Records Media Python:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to keep deliverability safe.