// This file is in the `Gradle Scripts` folder


plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    // Defines the Android SDK version your code is compiled against
    compileSdk = 34
    namespace = "com.example.helloworld"
    defaultConfig {
        // Unique identifier for your app on the Google Play Store
        applicationId = "com.example.helloworld"
        // Minimum Android version the app will run on
        minSdk = 24
        // Target Android version (usually the latest)
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    kotlinOptions {
        jvmTarget = "1.8"
    }
}

// DEPENDENCIES block: This is where you add external libraries
dependencies {

    // Default Android and Kotlin libraries
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.appcompat:appcompat:1.6.1")
    implementation("com.google.android.material:material:1.10.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Testing dependencies
    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.1.5")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.5.1")
}