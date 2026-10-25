package com.safesmartmaps.watch

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Build
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowManager
import android.widget.Button
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.concurrent.Executors

/**
 * Small screens for a round watch, one action each:
 *  1. type the 6-digit code from the phone  2. walking status  3. "Are you OK?"  4. alert sent.
 * Built in code (no layout files, no Compose) to keep the app tiny.
 */
class MainActivity : Activity() {
    private val network = Executors.newSingleThreadExecutor()
    private val relay = RelayClient(BuildConfig.RELAY_URL)
    private val refresh: () -> Unit = { runOnUiThread { render() } }

    private var code = ""
    private var message: String? = null
    private var pairing = false
    private lateinit var root: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(28), dp(24), dp(28), dp(24))
        }
        setContentView(ScrollView(this).apply {
            setBackgroundColor(Color.BLACK)
            addView(root, ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
        })
        render()
    }

    override fun onStart() {
        super.onStart()
        Session.addListener(refresh)
        render()
    }

    override fun onStop() {
        Session.removeListener(refresh)
        super.onStop()
    }

    override fun onDestroy() {
        network.shutdown()
        super.onDestroy()
    }

    // ---- screens ----

    private fun render() {
        root.removeAllViews()
        val state = Session.controller?.state
        when {
            state == null -> renderCodeEntry()
            state.phase == Phase.PROMPT -> renderPrompt(state)
            state.phase == Phase.ALERT_SENT -> renderAlertSent()
            else -> renderWalking(state)
        }
        if (state != null && state.phase != Phase.WALKING) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else {
            window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        }
    }

    private fun renderCodeEntry() {
        root.addView(text("Enter code from phone", 13f, Color.LTGRAY))
        root.addView(text(code.padEnd(6, '·').chunked(3).joinToString(" "), 26f, Color.WHITE))
        message?.let { root.addView(text(it, 12f, Color.rgb(255, 200, 80))) }
        val pad = GridLayout(this).apply { columnCount = 3 }
        for (d in listOf("1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK")) {
            pad.addView(button(d, width = dp(52)) { onPadKey(d) })
        }
        root.addView(pad)
    }

    private fun renderWalking(state: WalkState) {
        root.addView(text("Walking", 13f, Color.LTGRAY))
        root.addView(text(state.bpm?.let { "$it bpm" } ?: "Waiting…", 30f, Color.WHITE))
        val note = Session.note ?: if (state.baseline == null) "Learning your normal rate…" else "Watching for unusual rate"
        root.addView(text(note, 11f, Color.LTGRAY))
        root.addView(button("Test alert") { Session.controller?.forcePrompt(System.currentTimeMillis()) })
        root.addView(button("Stop") { HeartRateService.stop(this) })
    }

    private fun renderPrompt(state: WalkState) {
        root.addView(text("Are you OK?", 20f, Color.WHITE))
        root.addView(text("${state.secondsLeft}s", 14f, Color.rgb(255, 200, 80)))
        root.addView(button("I'm OK", bg = Color.rgb(30, 140, 80)) { Session.controller?.userOk() })
    }

    private fun renderAlertSent() {
        root.addView(text("Alert sent (demo)", 18f, Color.rgb(255, 200, 80)))
        root.addView(text("Nothing is really sent yet.", 11f, Color.LTGRAY))
        root.addView(button("Cancel, I'm OK") { Session.controller?.userOk() })
    }

    // ---- pairing ----

    private fun onPadKey(key: String) {
        when (key) {
            "⌫" -> code = code.dropLast(1)
            "OK" -> { if (code.length == 6) startPairing() else message = "Type all 6 digits." }
            else -> if (code.length < 6) code += key
        }
        if (key != "OK") message = null
        render()
    }

    private fun startPairing() {
        if (pairing) return
        val missing = neededPermissions().filter { checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isNotEmpty()) {
            requestPermissions(missing.toTypedArray(), REQUEST_PERMISSIONS)
            message = "Allow access, then press OK again."
            return
        }
        pairing = true
        message = "Pairing…"
        val entered = code
        network.execute {
            val outcome = relay.pair(entered)
            runOnUiThread {
                pairing = false
                when (outcome) {
                    is PairOutcome.Success -> {
                        Session.link = relay.link(outcome.token, outcome.tripId) {
                            runOnUiThread { HeartRateService.stop(this) }
                        }
                        code = ""
                        message = null
                        HeartRateService.start(this)
                    }
                    PairOutcome.BadCode -> message = "Wrong code. Check the phone."
                    PairOutcome.TooManyAttempts -> message = "Too many tries. Wait a minute."
                    PairOutcome.NetworkError -> message = "No connection. Try again."
                }
                render()
            }
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        val bodyOk = checkSelfPermission(Manifest.permission.BODY_SENSORS) == PackageManager.PERMISSION_GRANTED
        message = if (bodyOk) "Press OK to pair." else "Heart-rate access is needed."
        render()
    }

    private fun neededPermissions(): List<String> {
        val list = mutableListOf(Manifest.permission.BODY_SENSORS, Manifest.permission.ACTIVITY_RECOGNITION)
        if (Build.VERSION.SDK_INT >= 33) list += Manifest.permission.POST_NOTIFICATIONS
        return list
    }

    // ---- small view helpers ----

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun text(s: String, sizeSp: Float, color: Int) = TextView(this).apply {
        text = s
        textSize = sizeSp
        setTextColor(color)
        gravity = Gravity.CENTER
        setPadding(0, dp(4), 0, dp(4))
    }

    private fun button(label: String, bg: Int = Color.DKGRAY, width: Int = ViewGroup.LayoutParams.MATCH_PARENT,
                       onClick: () -> Unit) = Button(this).apply {
        text = label
        textSize = 13f
        setTextColor(Color.WHITE)
        setBackgroundColor(bg)
        minHeight = dp(40)
        minimumHeight = dp(40)
        layoutParams = LinearLayout.LayoutParams(width, ViewGroup.LayoutParams.WRAP_CONTENT).also {
            it.setMargins(dp(2), dp(2), dp(2), dp(2))
        }
        setOnClickListener { onClick() }
        visibility = View.VISIBLE
    }

    companion object {
        private const val REQUEST_PERMISSIONS = 7
    }
}
