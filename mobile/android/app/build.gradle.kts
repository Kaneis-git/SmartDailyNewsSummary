import java.util.Base64
import java.util.Properties
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("dev.flutter.flutter-gradle-plugin")
}
val defines = (project.findProperty("dart-defines") as? String ?: "").split(",").filter { it.isNotBlank() }.associate {
    val value = String(Base64.getDecoder().decode(it), Charsets.UTF_8).split("=", limit = 2)
    value[0] to value.getOrElse(1) { "" }
}
val signingFile = rootProject.file("key.properties")
val signingValues = Properties().apply { if (signingFile.exists()) signingFile.inputStream().use { load(it) } }
android {
    namespace = "cn.ainews.ai_daily_news"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    defaultConfig {
        applicationId = "cn.ainews.ai_daily_news"
        minSdk = 24
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
        manifestPlaceholders["JPUSH_PKGNAME"] = "cn.ainews.ai_daily_news"
        manifestPlaceholders["JPUSH_APPKEY"] = defines["JPUSH_APPKEY"].orEmpty()
        manifestPlaceholders["JPUSH_CHANNEL"] = "daily-news"
    }
    signingConfigs {
        if (signingFile.exists()) {
            create("production") {
                keyAlias = signingValues.getProperty("keyAlias")
                keyPassword = signingValues.getProperty("keyPassword")
                storeFile = file(signingValues.getProperty("storeFile"))
                storePassword = signingValues.getProperty("storePassword")
            }
        }
    }
    buildTypes {
        release {
            signingConfig = if (signingFile.exists()) signingConfigs.getByName("production") else null
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
}
kotlin { compilerOptions { jvmTarget = org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17 } }
flutter { source = "../.." }
gradle.taskGraph.whenReady {
    if (allTasks.any { it.name.contains("Release") } && !signingFile.exists()) throw GradleException("Release requires android/key.properties; see mobile/README.md")
    if (allTasks.any { it.name.contains("Release") } && !defines["API_BASE_URL"].orEmpty().startsWith("https://")) throw GradleException("Release requires HTTPS API_BASE_URL")
}
