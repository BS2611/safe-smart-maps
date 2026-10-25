package com.safesmartmaps.watch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

private class RecordingLink : WatchLink {
    val log = mutableListOf<String>()
    override fun heartbeat(bpm: Int, tsIso: String) { log += "beat:$bpm" }
    override fun prompt() { log += "prompt" }
    override fun alert() { log += "alert" }
    override fun ack(ok: Boolean) { log += "ack:$ok" }
}

class WalkControllerTest {
    private fun make(link: RecordingLink, prompts: MutableList<Int>? = null) =
        WalkController(link, TriggerDetector(), promptSeconds = 30, heartbeatEveryMs = 2_000,
            onPrompt = { prompts?.add(1) })

    @Test
    fun readingsAreSentAtMostEveryTwoSeconds() {
        val link = RecordingLink()
        val walk = make(link)
        walk.onSample(0, 80, 100)
        walk.onSample(500, 81, 100)
        walk.onSample(1_000, 82, 100)
        walk.onSample(2_000, 83, 100)
        assertEquals(listOf("beat:80", "beat:83"), link.log)
        assertEquals(83, walk.state.bpm)
    }

    @Test
    fun testButtonShowsThePromptAndTellsTheBackend() {
        val link = RecordingLink()
        val prompts = mutableListOf<Int>()
        val walk = make(link, prompts)
        walk.forcePrompt(1_000)
        assertEquals(Phase.PROMPT, walk.state.phase)
        assertEquals(30, walk.state.secondsLeft)
        assertEquals(listOf("prompt"), link.log)
        assertEquals(1, prompts.size)
    }

    @Test
    fun answeringOkCancelsTheAlert() {
        val link = RecordingLink()
        val walk = make(link)
        walk.forcePrompt(0)
        walk.tick(10_000)
        assertEquals(20, walk.state.secondsLeft)
        walk.userOk()
        walk.tick(60_000)
        assertEquals(Phase.WALKING, walk.state.phase)
        assertEquals(listOf("prompt", "ack:true"), link.log)
    }

    @Test
    fun noAnswerIn30SecondsSendsTheAlertOnce() {
        val link = RecordingLink()
        val walk = make(link)
        walk.forcePrompt(0)
        walk.tick(29_000)
        assertEquals(Phase.PROMPT, walk.state.phase)
        walk.tick(30_000)
        walk.tick(31_000)
        assertEquals(Phase.ALERT_SENT, walk.state.phase)
        assertEquals(listOf("prompt", "alert"), link.log)
    }

    @Test
    fun cancelAfterAlertReturnsToWalking() {
        val link = RecordingLink()
        val walk = make(link)
        walk.forcePrompt(0)
        walk.tick(31_000)
        walk.userOk()
        assertEquals(Phase.WALKING, walk.state.phase)
        assertTrue(link.log.last() == "ack:true")
    }

    @Test
    fun aSecondPromptIsIgnoredWhileOneIsShowing() {
        val link = RecordingLink()
        val walk = make(link)
        walk.forcePrompt(0)
        walk.forcePrompt(5_000)
        assertEquals(listOf("prompt"), link.log)
    }

    @Test
    fun theRealTriggerStartsThePrompt() {
        val link = RecordingLink()
        val detector = TriggerDetector(baselineWindowMs = 10_000, baselineMinSamples = 5, sustainMs = 4_000,
            signWindowMs = 6_000)
        val walk = WalkController(link, detector, heartbeatEveryMs = 60_000)
        var t = 0L
        while (t <= 10_000) { walk.onSample(t, 80, 100); t += 1_000 }
        repeat(8) { walk.onSample(t, 130, 170); t += 1_000 }
        assertEquals(Phase.PROMPT, walk.state.phase)
    }
}
