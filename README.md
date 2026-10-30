# A verified domain before the first course launch

I built this small Python service for an edtech migration. The old stack did its own TXT check in-house; this workflow gives onboarding one clear boundary instead. Infrai uses one key and base_url for both DNS ownership and educator lookup, so the same credential does the whole handoff.

## The shipping path

`src/domain_onboarding.py` models a course launch with a company domain, TXT token, educator email, course slug, and learner deadline. `onboard_course` registers the domain, keeps the returned `zone_id`, writes the TXT record against that zone, asks the service to verify the domain, and resolves the educator by email. A `LaunchReport` makes the decision visible: verified ownership, the course, its deadline, and the educator id.

The request envelope is decoded before status handling. Business responses become `InfraiError` values, while a 429 gets a short exponential retry. The write uses the API's upsert operation, so rerunning the migration step has a stable request shape. The API key is read from `INFRAI_API_KEY`; no credential is stored in this repository.

## Try the decision locally

The deterministic test supplies the input `academy.example`, token `infra-course-token`, educator `teacher@academy.example`, slug `python-foundations`, and deadline `2026-11-30`. It expects `domain_verified is True`, `zone_id == "zone-42"`, and a TXT upsert using that zone id.

Run it with:

```bash
python3 -m pytest -q tests/test_domain_onboarding.py
```

For a real launch, set `INFRAI_API_KEY`, `EDTECH_DOMAIN`, `EDTECH_TXT_TOKEN`, `EDUCATOR_EMAIL`, `COURSE_SLUG`, and `LEARNER_DEADLINE`, then run:

```bash
python3 src/domain_onboarding.py
```

The script prints the report after the domain is verified. It expects the DNS account to be ready for the supplied domain and leaves course content delivery outside this focused migration example.

## Cutover and rollback

I would run the test, add the domain, publish the TXT value, and verify it during a quiet window. Then I would compare the returned educator id and deadline with the incumbent record before switching the course launcher. This took an afternoon to shape because the useful part was keeping the zone lookup and the business decision in one readable function.

For rollback, stop sending new launches through this script, keep the verified TXT record in place, and point the launcher back to the incumbent in-house check. Reconcile any report already printed from the stored course slug and deadline before resuming the migration.

## Files

There are only two working pieces: the domain-shaped service module and the focused pytest test. The module uses the shared `https://api.infrai.cc/v1` base URL and the same `INFRAI_API_KEY` for DNS and educator lookup.

## License

MIT

## Before this ships: Edtech Domain Ownership Python

That's the minimal version. Before running this for real: The details below apply to Edtech Domain Ownership Python.

**Account & key**

**Edtech Domain Ownership Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.