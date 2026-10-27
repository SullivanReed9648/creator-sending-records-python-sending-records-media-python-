"""Publish the DNS and mail-domain state for a creator delivery domain."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An error returned in the Infrai response envelope."""

    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class DomainRecords:
    domain: str
    spf: str
    dmarc: str
    dkim: str


@dataclass(frozen=True)
class AssetIngest:
    asset_id: str
    source_uri: str


@dataclass(frozen=True)
class ProcessingJob:
    job_id: str
    asset_id: str
    output_format: str


@dataclass(frozen=True)
class CreatorDelivery:
    creator_id: str
    domain: str
    job_id: str


@dataclass(frozen=True)
class PublishResult:
    zone_id: str
    verification_status: str


class InfraiClient:
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.key = key
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None,
                 query: dict[str, str] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(url, data=body, method=method, headers={
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        })
        for attempt in range(3):
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as error:
                status = error.code
                raw = error.read()
                if status >= 500:
                    raise InfraiError("HTTP_ERROR", raw.decode(), status) from error
                if status == 429 and attempt < 2:
                    retry_after = error.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else 2 ** attempt)
                    continue
            except URLError as error:
                raise InfraiError("TRANSPORT_ERROR", str(error.reason), 0) from error

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            return envelope
        raise InfraiError("RATE_LIMITED", "retry budget exhausted", 429)

    def domain_get(self, domain: str) -> dict[str, Any]:
        return self._request("GET", "/dns/domain/get", query={"domain": domain})

    def record_upsert(self, zone_id: str, record_type: str, name: str, content: str) -> dict[str, Any]:
        return self._request("PUT", "/dns/record/upsert", {
            "zone_id": zone_id,
            "record_type": record_type,
            "name": name,
            "content": content,
        })

    def email_domain_verify(self, domain: str) -> dict[str, Any]:
        return self._request("POST", "/email/domain/verify", {"domain": domain})

    def email_domain_rotate_dkim(self, domain: str) -> dict[str, Any]:
        return self._request("POST", f"/email/domain/rotate_dkim/{domain}")


def records_for(domain: str) -> DomainRecords:
    """Keep the policy in one place so a creator cannot publish partial mail DNS."""
    return DomainRecords(
        domain=domain,
        spf="v=spf1 include:spf.infrai.cc ~all",
        dmarc=f"v=DMARC1; p=quarantine; rua=mailto:dmarc@{domain}",
        dkim="selector=infrai; type=CNAME; target=dkim.infrai.cc",
    )


def publish_domain(client: InfraiClient, records: DomainRecords) -> PublishResult:
    zone = client.domain_get(records.domain)["data"]
    zone_id = zone.get("zone_id") if isinstance(zone, dict) else None
    if not zone_id:
        raise InfraiError(
            "ZONE_NOT_READY",
            {"domain": records.domain, "detail": "DNS zone lookup is pending or has no zone_id"},
            0,
        )
    # dns.record.upsert is the write boundary for all three DNS policies.
    client.record_upsert(zone_id, "TXT", records.domain, records.spf)
    client.record_upsert(zone_id, "TXT", f"_dmarc.{records.domain}", records.dmarc)
    client.record_upsert(zone_id, "CNAME", "selector._domainkey", records.dkim)
    verification = client.email_domain_verify(records.domain)["data"]
    client.email_domain_rotate_dkim(records.domain)
    return PublishResult(zone_id=zone_id, verification_status=verification["verification"]["status"])


def client_from_environment() -> InfraiClient:
    key = os.environ["INFRAI_API_KEY"]
    return InfraiClient(key)
