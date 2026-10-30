import json

from src.domain_onboarding import CourseLaunch, InfraiClient, onboard_course


class FakeClient(InfraiClient):
    def __init__(self):
        super().__init__("test-key")
        self.calls = []

    def request(self, method, path, *, body=None, query=None):
        self.calls.append((method, path, body, query))
        if path == "/dns/domain/add":
            return {"ok": True, "data": {"zone_id": "zone-42"}}
        if path == "/dns/domain/verify":
            return {"ok": True, "data": {"verified": True}}
        if path == "/auth/user/get_by_email":
            return {"ok": True, "data": {"id": "educator-7"}}
        return {"ok": True, "data": {}}


def test_verified_domain_unlocks_course_launch_report():
    client = FakeClient()
    report = onboard_course(client, CourseLaunch(
        "academy.example", "infra-course-token", "teacher@academy.example",
        "python-foundations", "2026-11-30",
    ))

    assert report.domain_verified is True
    assert report.zone_id == "zone-42"
    assert report.educator_user_id == "educator-7"
    record_call = client.calls[1]
    assert record_call[0:2] == ("PUT", "/dns/record/upsert")
    assert record_call[2]["zone_id"] == "zone-42"
    assert record_call[2]["record_type"] == "TXT"
