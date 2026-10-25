package com.safesmartmaps.watch

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import androidx.health.services.client.ExerciseUpdateCallback
import androidx.health.services.client.HealthServices
import androidx.health.services.client.MeasureCallback
import androidx.health.services.client.data.Availability
import androidx.health.services.client.data.DataPointContainer
import androidx.health.services.client.data.DataType
import androidx.health.services.client.data.DeltaDataType
import androidx.health.services.client.data.ExerciseConfig
import androidx.health.services.client.data.ExerciseLapSummary
import androidx.health.services.client.data.ExerciseType
import androidx.health.services.client.data.ExerciseUpdate
import java.util.concurrent.Executors

/**
 * Keeps reading the heart-rate sensor while the screen is off. It uses a "walking" exercise so Health
 * Services keeps delivering heart rate and step cadence. If another app already owns the sensor
 * session, it falls back to plain heart-rate readings (no cadence, so only the Test button can prompt).
 */
class HeartRateService : Service() {
    private val main = Handler(Looper.getMainLooper())
    private val network = Executors.newSingleThreadExecutor()
    private var lastCadence: Int? = null
    private var usingExercise = false
    private var stopped = false

    private val ticker = object : Runnable {
        override fun run() {
            Session.controller?.tick(System.currentTimeMillis())
            if (!stopped) main.postDelayed(this, 1000)
        }
    }

    private val exerciseCallback = object : ExerciseUpdateCallback {
        override fun onExerciseUpdateReceived(update: ExerciseUpdate) {
            val bpm = update.latestMetrics.getData(DataType.HEART_RATE_BPM).lastOrNull()?.value?.toInt()
            update.latestMetrics.getData(DataType.STEPS_PER_MINUTE).lastOrNull()?.value?.let { lastCadence = it.toInt() }
            if (bpm != null) onReading(bpm, lastCadence)
        }
        override fun onLapSummaryReceived(lapSummary: ExerciseLapSummary) {}
        override fun onRegistered() {}
        override fun onRegistrationFailed(throwable: Throwable) { useMeasureFallback() }
        override fun onAvailabilityChanged(dataType: DataType<*, *>, availability: Availability) {}
    }

    private val measureCallback = object : MeasureCallback {
        override fun onAvailabilityChanged(dataType: DeltaDataType<*, *>, availability: Availability) {}
        override fun onDataReceived(data: DataPointContainer) {
            val bpm = data.getData(DataType.HEART_RATE_BPM).lastOrNull()?.value?.toInt()
            if (bpm != null) onReading(bpm, null)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            shutDown()
            return START_NOT_STICKY
        }
        val link = Session.link
        if (link == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        startInForeground()
        stopped = false
        Session.controller = WalkController(
            link = AsyncLink(link) { job -> network.execute(job) },
            onState = { Session.changed() },
            onPrompt = { buzz() },
        )
        Session.changed()
        startSensors()
        main.removeCallbacks(ticker)
        main.postDelayed(ticker, 1000)
        return START_NOT_STICKY
    }

    private fun onReading(bpm: Int, cadence: Int?) {
        main.post { Session.controller?.onSample(System.currentTimeMillis(), bpm, cadence) }
    }

    private fun startSensors() {
        try {
            val client = HealthServices.getClient(this).exerciseClient
            client.setUpdateCallback(exerciseCallback)
            val config = ExerciseConfig(
                exerciseType = ExerciseType.WALKING,
                dataTypes = setOf(DataType.HEART_RATE_BPM, DataType.STEPS_PER_MINUTE),
                isAutoPauseAndResumeEnabled = false,
                isGpsEnabled = false,
            )
            client.startExerciseAsync(config)
            usingExercise = true
        } catch (e: Exception) {
            useMeasureFallback()
        }
    }

    private fun useMeasureFallback() {
        usingExercise = false
        Session.note = "Using basic heart-rate mode (no step data)."
        main.post { Session.changed() }
        try {
            HealthServices.getClient(this).measureClient
                .registerMeasureCallback(DataType.HEART_RATE_BPM, measureCallback)
        } catch (e: Exception) {
            Session.note = "Heart-rate sensor is not available. Use the Test button."
            main.post { Session.changed() }
        }
    }

    private fun shutDown() {
        stopped = true
        main.removeCallbacks(ticker)
        try {
            val hs = HealthServices.getClient(this)
            if (usingExercise) {
                hs.exerciseClient.endExerciseAsync()
                hs.exerciseClient.clearUpdateCallbackAsync(exerciseCallback)
            } else {
                hs.measureClient.unregisterMeasureCallbackAsync(DataType.HEART_RATE_BPM, measureCallback)
            }
        } catch (_: Exception) {
            // sensor already released
        }
        Session.clear()
        stopForeground(STOP_FOREGROUND_REMOVE)
        stopSelf()
    }

    override fun onDestroy() {
        stopped = true
        main.removeCallbacks(ticker)
        network.shutdown()
        super.onDestroy()
    }

    private fun startInForeground() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "Walk check", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = Notification.Builder(this, CHANNEL)
            .setContentTitle("Walk check is on")
            .setContentText("Heart rate is used during this walk only.")
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setContentIntent(open)
            .build()
        if (Build.VERSION.SDK_INT >= 29) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_HEALTH)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun buzz() {
        val vibrator: Vibrator = if (Build.VERSION.SDK_INT >= 31) {
            getSystemService(VibratorManager::class.java).defaultVibrator
        } else {
            @Suppress("DEPRECATION") getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        }
        vibrator.vibrate(VibrationEffect.createWaveform(longArrayOf(0, 400, 200, 400, 200, 400), -1))
    }

    companion object {
        const val ACTION_STOP = "com.safesmartmaps.watch.STOP"
        private const val CHANNEL = "walk_check"
        private const val NOTIFICATION_ID = 1

        fun start(context: Context) {
            context.startForegroundService(Intent(context, HeartRateService::class.java))
        }

        fun stop(context: Context) {
            context.startService(Intent(context, HeartRateService::class.java).setAction(ACTION_STOP))
        }
    }
}
