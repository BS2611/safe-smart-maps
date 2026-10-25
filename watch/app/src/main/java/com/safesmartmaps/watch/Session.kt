package com.safesmartmaps.watch

import java.util.concurrent.CopyOnWriteArrayList

/**
 * What the screen and the background service share while a walk runs. Memory only: nothing is saved,
 * and everything is cleared when the walk stops (heart rate is health data).
 */
object Session {
    var link: WatchLink? = null
    var controller: WalkController? = null

    /** Shown under the heart rate, e.g. "Heart-rate sensor not available". */
    var note: String? = null

    private val listeners = CopyOnWriteArrayList<() -> Unit>()

    fun addListener(l: () -> Unit) { listeners += l }
    fun removeListener(l: () -> Unit) { listeners -= l }
    fun changed() = listeners.forEach { it() }

    val active: Boolean get() = controller != null

    fun clear() {
        link = null
        controller = null
        note = null
        changed()
    }
}

/** Runs backend calls off the main thread, one at a time and in order. */
class AsyncLink(private val inner: WatchLink, private val run: (() -> Unit) -> Unit) : WatchLink {
    override fun heartbeat(bpm: Int, tsIso: String) = run { inner.heartbeat(bpm, tsIso) }
    override fun prompt() = run { inner.prompt() }
    override fun alert() = run { inner.alert() }
    override fun ack(ok: Boolean) = run { inner.ack(ok) }
}
