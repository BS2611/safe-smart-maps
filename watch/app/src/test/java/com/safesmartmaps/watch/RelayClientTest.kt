package com.safesmartmaps.watch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private class FakeHttp(var reply: HttpResult = HttpResult(204, ""), var fail: Boolean = false) : Http {
    val calls = mutableListOf<Triple<String, String?, String?>>()
    override fun post(url: String, jsonBody: String?, bearer: String?): HttpResult {
        calls += Triple(url, jsonBody, bearer)
        if (fail) throw java.io.IOException("offline")
        return reply
    }
}

class RelayClientTest {
    @Test
    fun pairSuccessReadsTokenAndTrip() {
        val http = FakeHttp(HttpResult(200, "{\"watch_token\":\"tok123\",\"trip_id\":\"abc\"}"))
        val out = RelayClient("http://x", http).pair("123456")
        assertEquals(PairOutcome.Success("tok123", "abc"), out)
        assertEquals("http://x/v1/watch/pair", http.calls[0].first)
        assertEquals("{\"pair_code\":\"123456\",\"device\":\"wearos\"}", http.calls[0].second)
        assertNull(http.calls[0].third)
    }

    @Test
    fun pairMapsErrors() {
        val http = FakeHttp(HttpResult(400, "{}"))
        val client = RelayClient("http://x", http)
        assertEquals(PairOutcome.BadCode, client.pair("000000"))
        http.reply = HttpResult(429, "{}")
        assertEquals(PairOutcome.TooManyAttempts, client.pair("000000"))
        http.reply = HttpResult(500, "")
        assertEquals(PairOutcome.NetworkError, client.pair("000000"))
        http.fail = true
        assertEquals(PairOutcome.NetworkError, client.pair("000000"))
    }

    @Test
    fun heartbeatSendsBearerTokenAndWearosSource() {
        val http = FakeHttp()
        RelayClient("http://x", http).link("tok", "trip1").heartbeat(88, "2026-10-25T10:00:00Z")
        val (url, body, bearer) = http.calls[0]
        assertEquals("http://x/v1/watch/heartbeat", url)
        assertEquals("tok", bearer)
        assertEquals("{\"bpm\":88,\"ts\":\"2026-10-25T10:00:00Z\",\"source\":\"wearos\"}", body)
    }

    @Test
    fun alertAndAckCarryTheTripId() {
        val http = FakeHttp()
        val link = RelayClient("http://x", http).link("tok", "trip1")
        link.alert()
        link.ack(true)
        link.prompt()
        assertEquals("{\"trip_id\":\"trip1\"}", http.calls[0].second)
        assertEquals("{\"trip_id\":\"trip1\",\"ok\":true}", http.calls[1].second)
        assertTrue(http.calls[2].first.endsWith("/v1/watch/prompt"))
    }

    @Test
    fun offlineSendsDoNotCrash() {
        val http = FakeHttp(fail = true)
        val link = RelayClient("http://x", http).link("tok", "trip1")
        link.heartbeat(80, "t")
        link.alert()
        assertEquals(2, http.calls.size)
    }

    @Test
    fun serverSayingTheTripEndedStopsTheWalk() {
        val http = FakeHttp(HttpResult(401, "{}"))
        var ended = 0
        val link = RelayClient("http://x", http).link("tok", "trip1") { ended++ }
        link.heartbeat(80, "t")
        http.reply = HttpResult(404, "{}")
        link.alert()
        http.reply = HttpResult(204, "")
        link.heartbeat(80, "t")
        assertEquals(2, ended)
    }
}
