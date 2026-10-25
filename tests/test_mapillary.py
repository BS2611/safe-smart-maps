"""Mapillary photo source. API answers are hand-written FIXTURES via httpx.MockTransport."""
from datetime import datetime, timezone

import httpx

from server.data.mapillary import ATTRIBUTION, MapillaryPhotoSource, pick_best

NOW = datetime(2026, 10, 25, tzinfo=timezone.utc)
LAT, LNG = 37.8, -122.45


def ms(year):
    return int(datetime(year, 6, 1, tzinfo=timezone.utc).timestamp() * 1000)


def img(id, dlat=0.0, year=2025, pano=False, thumb="https://img/x.jpg"):
    return {"id": id, "captured_at": ms(year), "is_pano": pano, "thumb_1024_url": thumb,
            "computed_geometry": {"coordinates": [LNG, LAT + dlat]}}


def test_pick_best_prefers_nearest_flat_recent_photo():
    near_old = img("old", 0.00001, year=2010)
    pano = img("pano", 0.00001, pano=True)
    far = img("far", 0.0003)
    near = img("near", 0.0001)
    assert pick_best([near_old, pano, far, near], LAT, LNG, 5, NOW)["id"] == "near"
    assert pick_best([near_old, pano], LAT, LNG, 5, NOW) is None
    assert pick_best([{"id": "x"}], LAT, LNG, 5, NOW) is None


def test_pick_best_breaks_distance_ties_with_newer_photo():
    a, b = img("a", year=2022), img("b", year=2025)
    assert pick_best([a, b], LAT, LNG, 5, NOW)["id"] == "b"


def source(handler, token="fixture-token"):
    return MapillarySource(token, httpx.Client(transport=httpx.MockTransport(handler)))


def MapillarySource(token, client):  # noqa: N802 - small test helper
    return MapillaryPhotoSource(token=token, client=client)


def test_photo_near_downloads_the_thumbnail_and_labels_it():
    def handler(request):
        if request.url.host == "graph.mapillary.com":
            assert request.url.params["bbox"] and request.url.params["access_token"] == "fixture-token"
            return httpx.Response(200, json={"data": [img("123", 0.00005)]})
        return httpx.Response(200, content=b"\xff\xd8jpeg")

    photo = source(handler).photo_near(LAT, LNG)
    assert photo.id == "123" and photo.jpeg == b"\xff\xd8jpeg"
    assert photo.attribution == ATTRIBUTION and photo.captured_at.startswith("2025")


def test_failures_and_missing_token_mean_no_photo(monkeypatch):
    monkeypatch.delenv("MAPILLARY_TOKEN", raising=False)
    assert source(lambda r: httpx.Response(200, json={"data": []}), token=None).photo_near(LAT, LNG) is None
    for response in (httpx.Response(401), httpx.Response(200, text="oops"), httpx.Response(200, json={"data": []})):
        assert source(lambda r, x=response: x).photo_near(LAT, LNG) is None

    def down(request):
        raise httpx.ConnectError("down")

    assert source(down).photo_near(LAT, LNG) is None


def test_thumbnail_download_failure_means_no_photo():
    def handler(request):
        if request.url.host == "graph.mapillary.com":
            return httpx.Response(200, json={"data": [img("1", 0.00005)]})
        return httpx.Response(403)

    assert source(handler).photo_near(LAT, LNG) is None
