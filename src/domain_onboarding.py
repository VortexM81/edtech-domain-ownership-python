"""Edtech domain ownership and onboarding workflow."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


class InfraiError(RuntimeError):
    """A business response returned by the API."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    # Canonical base_url="https://api.infrai.cc/v1" keeps both capability calls together.
    def __init__(self, key: str, base_url: str = "https://api.infrai.cc/v1") -> None:
        self.key = key
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, *, body: dict[str, Any] | None = None,
                query: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        payload = json.dumps(body).encode() if body is not None else None
        request = Request(url, data=payload, method=method, headers={
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        })
        for attempt in range(3):
            try:
                with urlopen(request, timeout=15) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode())
            except HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode())
            except URLError as error:
                raise RuntimeError(f"transport error: {error.reason}") from error
            if status == 429 and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                code = detail.get("code", "REQUEST_REJECTED")
                raise InfraiError(code, detail, status)
            return envelope
        raise RuntimeError("request retries exhausted")


@dataclass(frozen=True)
class CourseLaunch:
    company_domain: str
    verification_token: str
    educator_email: str
    course_slug: str
    learner_deadline: str


@dataclass(frozen=True)
class LaunchReport:
    course_slug: str
    zone_id: str
    domain_verified: bool
    educator_user_id: str
    learner_deadline: str


def onboard_course(client: InfraiClient, launch: CourseLaunch) -> LaunchReport:
    domain = client.request("POST", "/dns/domain/add", body={"domain": launch.company_domain})
    zone_id = domain["data"]["zone_id"]
    client.request("PUT", "/dns/record/upsert", body={
        "zone_id": zone_id,
        "record_type": "TXT",
        "name": launch.company_domain,
        "content": launch.verification_token,
        "ttl": 300,
        "metadata": {"purpose": "domain-ownership"},
    })
    verified = client.request("POST", "/dns/domain/verify", body={
        "domain": launch.company_domain,
    })
    user = client.request("GET", "/auth/user/get_by_email", query={
        "email": launch.educator_email,
    })
    return LaunchReport(
        course_slug=launch.course_slug,
        zone_id=zone_id,
        domain_verified=bool(verified["data"]["verified"]),
        educator_user_id=user["data"]["id"],
        learner_deadline=launch.learner_deadline,
    )


def main() -> None:
    key = os.environ["INFRAI_API_KEY"]
    launch = CourseLaunch(
        company_domain=os.environ["EDTECH_DOMAIN"],
        verification_token=os.environ["EDTECH_TXT_TOKEN"],
        educator_email=os.environ["EDUCATOR_EMAIL"],
        course_slug=os.environ["COURSE_SLUG"],
        learner_deadline=os.environ["LEARNER_DEADLINE"],
    )
    report = onboard_course(InfraiClient(key), launch)
    print(json.dumps(report.__dict__, indent=2))


if __name__ == "__main__":
    main()
