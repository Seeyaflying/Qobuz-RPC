package com.example.myapplication.data

import kotlinx.serialization.Serializable

/**
 * The full payload sent from the Android app to the central API server.
 * This includes the track details AND the token needed to authorize the Discord API call.
 */
@Serializable
data class RpcPayload(
    // The Discord Access Token needed by the server to set the user's status
    val discordAccessToken: String,
    // The track details to be formatted for the Discord status
    val activity: DiscordActivity
)

// Reusing the internal Discord Activity structure
@Serializable
data class DiscordActivity(
    val details: String,
    val state: String,
    val timestamps: DiscordTimestamps,
    val assets: DiscordAssets
)
@Serializable
data class DiscordTimestamps(val start: Long?, val end: Long?)
@Serializable
data class DiscordAssets(
    val largeImage: String,
    val largeText: String?,
    val smallImage: String,
    val smallText: String?
)