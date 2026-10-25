package com.safesmartmaps.watch

import java.time.Instant

enum class Phase { WALKING, PROMPT, ALERT_SENT }

data class WalkState(val phase: Phase, val bpm: Int? = null, val secondsLeft: Int = 0, val baseline: Int? = null)

/**
 * The walk: sends readings, shows the "Are you OK?" prompt, and sends the alert if nobody answers.
 * No Android classes here, time is passed in, so it is unit tested. Call [tick] about once a second.
 */
class WalkController(
    private val link: WatchLink,
    private val detector: TriggerDetector = TriggerDetector(),
    private val promptSeconds: Int = 30,
    private val heartbeatEveryMs: Long = 2_000,
    private val onState: (WalkState) -> Unit = {},
    private val onPrompt: () -> Unit = {},
) {
    var state = WalkState(Phase.WALKING)
        private set
    private var promptDeadlineMs = 0L
    private var lastBeatMs = Long.MIN_VALUE

    fun onSample(nowMs: Long, bpm: Int, cadence: Int?) {
        if (lastBeatMs == Long.MIN_VALUE || nowMs - lastBeatMs >= heartbeatEveryMs) {
            lastBeatMs = nowMs
            link.heartbeat(bpm, Instant.ofEpochMilli(nowMs).toString())
        }
        val fired = detector.onSample(nowMs, bpm, cadence)
        update(state.copy(bpm = bpm, baseline = detector.baseline))
        if (fired && state.phase == Phase.WALKING) startPrompt(nowMs)
    }

    /** Demo button: show the prompt now without waiting for a real trigger. */
    fun forcePrompt(nowMs: Long) {
        if (state.phase == Phase.WALKING) startPrompt(nowMs)
    }

    /** "I'm OK" during the prompt, or "Cancel" after the alert. */
    fun userOk() {
        if (state.phase == Phase.WALKING) return
        link.ack(true)
        update(state.copy(phase = Phase.WALKING, secondsLeft = 0))
    }

    fun tick(nowMs: Long) {
        if (state.phase != Phase.PROMPT) return
        val left = ((promptDeadlineMs - nowMs + 999) / 1000).toInt()
        if (left > 0) {
            if (left != state.secondsLeft) update(state.copy(secondsLeft = left))
        } else {
            link.alert()
            update(state.copy(phase = Phase.ALERT_SENT, secondsLeft = 0))
        }
    }

    private fun startPrompt(nowMs: Long) {
        promptDeadlineMs = nowMs + promptSeconds * 1000L
        link.prompt()
        update(state.copy(phase = Phase.PROMPT, secondsLeft = promptSeconds))
        onPrompt()
    }

    private fun update(next: WalkState) {
        state = next
        onState(next)
    }
}
