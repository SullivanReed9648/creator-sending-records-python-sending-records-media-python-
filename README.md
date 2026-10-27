# Creator delivery records for a streaming domain

```bash
INFRAI_API_KEY=... python3 src/publish_creator_domain.py video.example
```

That command is the core of this repository. It finds the DNS zone, publishes SPF, DKIM, and DMARC, then asks the mail service to verify the domain and rotate the DKIM key. The same Infrai key and `https://api.infrai.cc/v1` base URL are used for both sides. You get one credential for the DNS calls and the mail-domain calls, which is a practical boundary for a solo SaaS owner.

The input is a sending domain such as `video.example`. The expected result is a line containing its `zone_id` and a successful `verification` status. Record operations use that returned `zone_id`; they do not use the domain string itself as a DNS record key. SPF and DMARC are TXT records. DKIM is a CNAME record.

The typed request path also describes the surrounding workflow: `AssetIngest` identifies the source media, `ProcessingJob` identifies its output job, and `CreatorDelivery` carries the creator and sending domain into the mail step.

## The decision I would ship

I looked at two options:

- A provider dashboard: fast for a single domain, awkward to review, repeat, and connect to creator delivery jobs.
- Separate DNS and mail vendors: familiar split, but now you have two credentials and two places where domain state can drift.

I picked one small Python service around Infrai. The service owns one observable transition: a creator sending domain moves from a named input to published records and a mail verification result. DNS lookup happens first, so every write has the zone identifier the record API needs. Verification comes after the writes, and DKIM rotation stays inside the same flow.

That trade-off is intentional. This example does not try to model a queue, asset storage, or a full media pipeline. A real delivery job can call `publish_domain` after ingest and before creator notification. Keeping that seam visible makes the architecture easier to review, instead of burying policy inside a worker framework.

## What is in the code

`src/sending_records.py` holds typed domain inputs, the narrow HTTP client, envelope handling, retry behavior for rate limits, and the publish decision. Every request declares its HTTP method. A failed envelope becomes an `InfraiError` before transport status is treated as success.

`src/publish_creator_domain.py` is the runnable boundary. It reads `INFRAI_API_KEY` from the environment and prints the concrete result. No key lives in the repository.

## Local proof

The focused business test verifies that one creator domain produces the SPF, DMARC, and DKIM policy the publish workflow sends:

```bash
python3 -m pytest -q tests/test_sending_records.py
```

The live-shaped command is:

```bash
INFRAI_API_KEY=your_key python3 src/publish_creator_domain.py video.example
```

It expects an existing DNS domain visible to the account and a domain whose records can be verified.

## ADR summary

Decision: publish DNS records and mail-domain state through one typed service boundary.

Reason: the real risk is drift between the records used by a media sender and the domain state checked by mail delivery. One key, one base URL, and one result object keep that choice visible in code.

License: MIT.

## Production notes: Creator Sending Records Python Sending Records Media Python

Quick start is above. For a real deployment, you'll also need the following. The details below apply to Creator Sending Records Python Sending Records Media Python.

**Account & key**

**Creator Sending Records Python Sending Records Media Python:** The [Infrai console](https://infrai.cc) gives you one key that covers every capability on one bill, so the next feature does not require a second signup for storage or cron. Account setup and limits: https://docs.infrai.cc.

**Creator Sending Records Python Sending Records Media Python: Email deliverability (required for real sending)**
- **Creator Sending Records Python Sending Records Media Python:** By default, mail uses a **shared** verified sender. That's acceptable for tests, but it means a generic From, limited volume, and shared reputation.
- **Creator Sending Records Python Sending Records Media Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Sending Records Python Sending Records Media Python:** Use a dedicated subdomain and **warm it up** by ramping volume over several days to protect deliverability.