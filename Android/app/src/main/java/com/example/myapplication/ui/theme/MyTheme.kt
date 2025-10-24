package com.example.myapplication.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

// Define your color schemes according to Material 3 guidelines
// These are example colors; you can customize them.
private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFFBB86FC), // A light purple
    secondary = Color(0xFF03DAC5), // A vibrant teal
    tertiary = Color(0xFF3700B3), // A deep purple
    background = Color(0xFF121212), // Standard dark background
    surface = Color(0xFF1E1E1E), // Slightly lighter than background for elevated surfaces
    onPrimary = Color.Black,
    onSecondary = Color.Black,
    onTertiary = Color.White,
    onBackground = Color.White,
    onSurface = Color.White,
    error = Color(0xFFCF6679) // A standard error red for dark themes
    // FIX: 'surfaceContainerHigh' has been removed.
    // The system will derive it automatically from the colors above.
)

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFF6200EE), // A strong purple
    secondary = Color(0xFF03DAC6), // A vibrant teal
    tertiary = Color(0xFF3700B3), // A deep purple
    background = Color(0xFFFFFFFF), // Standard light background
    surface = Color(0xFFFFFFFF), // Surfaces are the same as background in light theme
    onPrimary = Color.White,
    onSecondary = Color.Black,
    onTertiary = Color.White,
    onBackground = Color.Black,
    onSurface = Color.Black,
    error = Color(0xFFB00020) // A standard error red for light themes
    // FIX: 'surfaceContainerHigh' has been removed.
)

@Composable
fun MyTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+ but disabled here for consistency
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        // dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
        //     val context = LocalContext.current
        //     if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        // } // Dynamic color logic is commented out but can be enabled if needed.
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    // This block helps manage the status bar color to match the theme
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography, // Assumes you have a Typography.kt file
        content = content
    )
}
