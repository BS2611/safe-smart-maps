"""Claude street-photo audits inside the planner. Photo and model answers are labeled fakes."""
from server.services.audit import Photo, StretchAudit
from tests.test_planner import PlannerCase, request


class FakePhotos:
    def __init__(self, fail=False, none=False):
        self.fail, self.none, self.calls = fail, none, 0

    def photo_near(self, lat, lng):
        self.calls += 1
        if self.fail:
            raise RuntimeError("photo service down")
        return None if self.none else Photo(id=f"p{self.calls}", jpeg=b"x", captured_at="2025-06-01",
                                            attribution="CC BY-SA fixture")


class FakeAuditor:
    def __init__(self, result=True):
        self.result = result

    def audit(self, photo):
        if not self.result:
            return None
        return StretchAudit(photo.id, "yes", "no", "good", "no", "medium", "Two lamp posts.",
                            photo.captured_at, photo.attribution)


class AuditTests(PlannerCase):
    def plan(self, **kw):
        return self.planner(**kw).plan(request())

    def test_no_photo_source_or_auditor_means_no_audits(self):
        assert all(r.street_photo_audits == [] for r in self.plan().routes)
        assert all(r.street_photo_audits == [] for r in self.plan(auditor=FakeAuditor()).routes)
        assert all(r.street_photo_audits == [] for r in self.plan(photos=FakePhotos()).routes)

    def test_audits_cover_weak_stretches_only_on_the_first_route(self):
        resp = self.plan(auditor=FakeAuditor(), photos=FakePhotos())
        first, rest = resp.routes[0], resp.routes[1:]
        assert 0 < len(first.street_photo_audits) <= 3
        assert all(r.street_photo_audits == [] for r in rest)
        weak = {s.segment_id for s in first.segments if s.band != "green"}
        for a in first.street_photo_audits:
            assert a.segment_id in weak and a.photo_url.endswith(a.photo_id)
            assert "daytime" in a.label and a.attribution

    def test_failures_never_break_the_route_request(self):
        resp = self.plan(auditor=FakeAuditor(), photos=FakePhotos(fail=True))
        assert resp.routes and resp.routes[0].street_photo_audits == []
        assert self.plan(auditor=FakeAuditor(result=False), photos=FakePhotos()).routes[0].street_photo_audits == []
        assert self.plan(auditor=FakeAuditor(), photos=FakePhotos(none=True)).routes[0].street_photo_audits == []

    def test_audits_do_not_change_scores(self):
        plain = self.plan()
        audited = self.plan(auditor=FakeAuditor(), photos=FakePhotos())
        assert [r.route_score for r in plain.routes] == [r.route_score for r in audited.routes]
