package com.safesmartmaps.watch

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TriggerDetectorTest {
    // Short windows so the tests are quick; the rule is the same as the real defaults.
    private fun detector() = TriggerDetector(
        baselineWindowMs = 10_000, baselineMinSamples = 5, sustainMs = 4_000,
        signWindowMs = 6_000, cooldownMs = 30_000,
    )

    /** One reading per second from t=0 to t=10s at 80 bpm, walking at 100 steps/min. */
    private fun TriggerDetector.learnBaseline(): Long {
        var t = 0L
        while (t <= 10_000) {
            onSample(t, 80, 100)
            t += 1_000
        }
        return t
    }

    @Test
    fun noBaselineBeforeEnoughTimeAndReadings() {
        val d = detector()
        for (t in 0..4_000 step 1_000) assertFalse(d.onSample(t.toLong(), 150, 0))
        assertNull(d.baseline)
    }

    @Test
    fun baselineIsTheMedianOfTheFirstReadings() {
        val d = detector()
        d.learnBaseline()
        assertEquals(80, d.baseline)
    }

    @Test
    fun spikeAloneDoesNotTrigger() {
        val d = detector()
        var t = d.learnBaseline()
        var fired = false
        repeat(10) { fired = d.onSample(t, 130, 100) || fired; t += 1_000 } // still walking normally
        assertFalse(fired)
    }

    @Test
    fun spikeThenSuddenStopTriggers() {
        val d = detector()
        var t = d.learnBaseline()
        var fired = false
        repeat(3) { fired = d.onSample(t, 125, 100) || fired; t += 1_000 }
        repeat(8) { fired = d.onSample(t, 125, 0) || fired; t += 1_000 } // stopped
        assertTrue(fired)
    }

    @Test
    fun spikeWithVeryFastPaceTriggers() {
        val d = detector()
        var t = d.learnBaseline()
        var fired = false
        repeat(8) { fired = d.onSample(t, 130, 170) || fired; t += 1_000 }
        assertTrue(fired)
    }

    @Test
    fun slowRiseDoesNotTrigger() {
        val d = detector()
        var t = d.learnBaseline()
        var fired = false
        // 95 is only +15 over the baseline of 80, below the 25 bpm minimum rise
        repeat(10) { fired = d.onSample(t, 95, 0) || fired; t += 1_000 }
        assertFalse(fired)
    }

    @Test
    fun shortSpikeDoesNotTrigger() {
        val d = detector()
        var t = d.learnBaseline()
        var fired = d.onSample(t, 130, 0); t += 1_000
        fired = d.onSample(t, 82, 0) || fired; t += 1_000 // back to normal before it was sustained
        fired = d.onSample(t, 130, 0) || fired
        assertFalse(fired)
    }

    @Test
    fun coolDownStopsRepeatTriggers() {
        val d = detector()
        var t = d.learnBaseline()
        var fires = 0
        repeat(20) { if (d.onSample(t, 130, 170)) fires++; t += 1_000 }
        assertEquals(1, fires)
    }

    @Test
    fun noCadenceMeansNoSecondSign() {
        val d = detector()
        var t = d.learnBaseline()
        var fired = false
        repeat(15) { fired = d.onSample(t, 140, null) || fired; t += 1_000 }
        assertFalse(fired)
    }

    @Test
    fun resetForgetsTheBaseline() {
        val d = detector()
        d.learnBaseline()
        assertNotNull(d.baseline)
        d.reset()
        assertNull(d.baseline)
    }
}
