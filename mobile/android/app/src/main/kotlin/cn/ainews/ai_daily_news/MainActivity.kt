package cn.ainews.ai_daily_news

import android.Manifest
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var pending: MethodChannel.Result? = null
    private fun enabled(): Boolean = getSystemService(NotificationManager::class.java).areNotificationsEnabled()
    override fun configureFlutterEngine(engine: FlutterEngine) {
        super.configureFlutterEngine(engine)
        MethodChannel(engine.dartExecutor.binaryMessenger, "daily_news/notifications").setMethodCallHandler { call, result ->
            when (call.method) {
                "enabled" -> result.success(enabled())
                "request" -> {
                    if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                        if (pending != null) result.error("busy", "Permission request pending", null)
                        else { pending = result; requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 803) }
                    } else result.success(enabled())
                }
                "settings" -> {
                    val intent = if (Build.VERSION.SDK_INT >= 26) Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE, packageName)
                    else Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName"))
                    startActivity(intent)
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }
    }
    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, permissions, results)
        if (code == 803) { pending?.success(results.isNotEmpty() && results[0] == PackageManager.PERMISSION_GRANTED && enabled()); pending = null }
    }
    override fun onDestroy() {
        pending?.error("cancelled", "Activity closed", null)
        pending = null
        super.onDestroy()
    }
}
