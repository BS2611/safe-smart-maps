package com.safesmartmaps.watch

/**
 * Decides when a heart rate looks unusual for this walk. Pure logic (no Android) so it is unit tested.
 *
 * Rule (FUNCTIONAL_SPEC 5.7): the rate must rise well above the user's own walking baseline for a while
 * AND a second sign must be seen: a sudden stop after walking, or a very fast pace.
 * This is not a medical test. The wording on screen is "unusual heart rate", nothing more.
 */
class TriggerDetector(
    private val baselineWindowMs: Long = 60_000,
    private val baselineMinSamples: Int = 10,
    private val ratio: Double = 1.3,
    private val minRise: Int = 25,
    private val sustainMs: Long = 10_000,
    private val signWindowMs: Long = 15_000,
    private val cooldownMs: Long = 120_000,
    private val walkingCadence: Int = 60,
    private val stopCadence: Int = 10,
    private val fastCadence: Int = 150,
) {
    private val baselineSamples = mutableListOf<Int>()
    private var firstSampleMs: Long? = null
    private var lastWalkingMs: Long? = null
    private var lastSignMs: Long? = null
    private var elevatedSinceMs: Long? = null
    private var lastFireMs: Long? = null

    /** Null until enough readings were collected. */
    var baseline: Int? = null
        private set

    /** Feed one reading. Returns true when the "Are you OK?" prompt should show. */
    fun onSample(nowMs: Long, bpm: Int, cadence: Int?): Boolean {
        if (firstSampleMs == null) firstSampleMs = nowMs
        if (cadence != null && cadence >= walkingCadence) lastWalkingMs = nowMs

        if (baseline == null) {
            baselineSamples += bpm
            val ready = nowMs - firstSampleMs!! >= baselineWindowMs && baselineSamples.size >= baselineMinSamples
            if (ready) baseline = median(baselineSamples)
            return false
        }

        val base = baseline!!
        if (cadence != null) {
            val stoppedAfterWalking =
                cadence <= stopCadence && lastWalkingMs?.let { nowMs - it <= signWindowMs * 2 } == true
            if (stoppedAfterWalking || cadence >= fastCadence) lastSignMs = nowMs
        }

        val elevated = bpm >= base * ratio && bpm >= base + minRise
        if (!elevated) {
            elevatedSinceMs = null
            return false
        }
        if (elevatedSinceMs == null) elevatedSinceMs = nowMs

        val sustained = nowMs - elevatedSinceMs!! >= sustainMs
        val signSeen = lastSignMs?.let { nowMs - it <= signWindowMs } == true
        val coolingDown = lastFireMs?.let { nowMs - it < cooldownMs } == true
        if (sustained && signSeen && !coolingDown) {
            lastFireMs = nowMs
            elevatedSinceMs = null
            return true
        }
        return false
    }

    fun reset() {
        baselineSamples.clear()
        baseline = null
        firstSampleMs = null
        lastWalkingMs = null
        lastSignMs = null
        elevatedSinceMs = null
        lastFireMs = null
    }

    private fun median(values: List<Int>): Int {
        val sorted = values.sorted()
        val mid = sorted.size / 2
        return if (sorted.size % 2 == 1) sorted[mid] else (sorted[mid - 1] + sorted[mid]) / 2
    }
}
