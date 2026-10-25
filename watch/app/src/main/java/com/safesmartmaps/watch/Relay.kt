package com.safesmartmaps.watch

import java.net.HttpURLConnection
import java.net.URL

data class HttpResult(val code: Int, val body: String)

/** One HTTP call. A fake is used in unit tests. */
interface Http {
    fun post(url: String, jsonBody: String?, bearer: String?): HttpResult
}

class UrlConnectionHttp : Http {
    override fun post(url: String, jsonBody: String?, bearer: String?): HttpResult {
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.connectTimeout = 8_000
            conn.readTimeout = 8_000
            if (bearer != null) conn.setRequestProperty("Authorization", "Bearer $bearer")
            if (jsonBody != null) {
                conn.setRequestProperty("Content-Type", "application/json")
                conn.doOutput = true
                conn.outputStream.use { it.write(jsonBody.toByteArray()) }
            }
            val code = conn.responseCode
            val stream = if (code >= 400) conn.errorStream else conn.inputStream
            val text = stream?.bufferedReader()?.use { it.readText() } ?: ""
            return HttpResult(code, text)
        } finally {
            conn.disconnect()
        }
    }
}

sealed class PairOutcome {
    data class Success(val token: String, val tripId: String) : PairOutcome()
    object BadCode : PairOutcome()
    object TooManyAttempts : PairOutcome()
    object NetworkError : PairOutcome()
}

/** What the walk logic needs from the backend, already tied to one paired trip. */
interface WatchLink {
    fun heartbeat(bpm: Int, tsIso: String)
    fun prompt()
    fun alert()
    fun ack(ok: Boolean)
}

/** Talks to the relay endpoints in CONTRACTS.md. Heart rate is never logged here. */
class RelayClient(private val baseUrl: String, private val http: Http = UrlConnectionHttp()) {

    fun pair(code: String): PairOutcome {
        val res = try {
            http.post("$baseUrl/v1/watch/pair", "{\"pair_code\":\"$code\",\"device\":\"wearos\"}", null)
        } catch (e: Exception) {
            return PairOutcome.NetworkError
        }
        return when (res.code) {
            200 -> {
                val token = field(res.body, "watch_token")
                val trip = field(res.body, "trip_id")
                if (token != null && trip != null) PairOutcome.Success(token, trip) else PairOutcome.NetworkError
            }
            429 -> PairOutcome.TooManyAttempts
            400 -> PairOutcome.BadCode
            else -> PairOutcome.NetworkError
        }
    }

    /** [onEnded] runs when the server says the trip is over (the phone pressed Stop). */
    fun link(token: String, tripId: String, onEnded: () -> Unit = {}): WatchLink = object : WatchLink {
        private fun send(path: String, body: String?) {
            try {
                val res = http.post("$baseUrl$path", body, token)
                if (res.code == 401 || res.code == 404) onEnded()
            } catch (_: Exception) {
                // offline: the next reading tries again; the phone shows "no reading"
            }
        }

        override fun heartbeat(bpm: Int, tsIso: String) =
            send("/v1/watch/heartbeat", "{\"bpm\":$bpm,\"ts\":\"$tsIso\",\"source\":\"wearos\"}")

        override fun prompt() = send("/v1/watch/prompt", null)
        override fun alert() = send("/v1/alerts", "{\"trip_id\":\"$tripId\"}")
        override fun ack(ok: Boolean) = send("/v1/alerts/ack", "{\"trip_id\":\"$tripId\",\"ok\":$ok}")
    }

    companion object {
        /** Reads a string value from a small JSON object without needing a JSON library. */
        fun field(json: String, name: String): String? =
            Regex("\"" + name + "\"\\s*:\\s*\"([^\"]*)\"").find(json)?.groupValues?.get(1)
    }
}
