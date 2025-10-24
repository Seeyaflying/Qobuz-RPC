package com.example.myapplication.data

/**
 * Data class representing the current state of music playback and track information.
 * This structure holds all the information needed to update Discord Custom Status.
 */
data class TrackState(
    val title: String = "No Track Playing",
    val artist: String = "",
    val album: String = "",
    val isPlaying: Boolean = false,
    val durationSeconds: Long = 0,
    val positionSeconds: Long = 0,
    val albumArtUrl: String? = null,
    val hiResQuality: String? = null // e.g., "24-bit / 192 kHz"
) {
    /** Calculates the end timestamp in milliseconds for Discord RPC. */
    fun calculateEndTimeMillis(startTime: Long = System.currentTimeMillis()): Long? {
        if (!isPlaying || durationSeconds == 0L || positionSeconds >= durationSeconds) return null
        val remainingSeconds = durationSeconds - positionSeconds
        return startTime + (remainingSeconds * 1000)
    }

    /** Calculates the start timestamp in milliseconds for Discord RPC. */
    fun calculateStartTimeMillis(currentPlayheadMs: Long): Long? {
        if (!isPlaying || positionSeconds == 0L) return null
        return currentPlayheadMs - (positionSeconds * 1000)
    }
}