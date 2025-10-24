package com.example.myapplication.service

import android.content.Context
import android.util.Log
import com.example.myapplication.data.DiscordActivity
import com.example.myapplication.data.DiscordAssets
import com.example.myapplication.data.DiscordTimestamps
import com.example.myapplication.data.RpcPayload
import com.example.myapplication.data.TrackState
import io.ktor.client.*
import io.ktor.client.engine.android.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json

/**
 * Defines the real-time status of the connection (now a simple API status).
 */
enum class ConnectionStatus {
    OFFLINE, // Service not active
    READY, // Ready to send data
    SENDING, // Currently sending
    SUCCESS, // Last send successful
    ERROR // Last send failed
}

/**
 * Service to manage and send Rich Presence updates to a Centralized Management Server via REST API.
 */
class DiscordRpcService(
    private val context: Context,
    private val scope: CoroutineScope,
) {
    // *** IMPORTANT: REPLACE WITH YOUR MANAGED CLOUD API ENDPOINT ***
    private val API_BASE_URL = "https://your-qobuz-rpc-api.a.run.app/v1"

    private val _currentTrack = MutableStateFlow(TrackState())
    val currentTrack: StateFlow<TrackState> = _currentTrack

    private val _connectionStatus = MutableStateFlow(ConnectionStatus.READY)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus // Public status observable

    // Token must be set by MainActivity after successful OAuth
    var discordAccessToken: String? = null

    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                prettyPrint = true
                encodeDefaults = true
            })
        }
    }

    init {
        scope.launch {
            // Start listening to track updates to trigger API POST attempt
            currentTrack.collectLatest { track ->
                // Only attempt to send if a token is available
                if (discordAccessToken != null) {
                    sendRpcUpdate(track, discordAccessToken!!)
                } else {
                    Log.w("DiscordRpcService", "Skipping RPC update: Discord token is missing.")
                }
            }
        }
    }

    fun updateTrackState(newState: TrackState) {
        _currentTrack.value = newState
    }

    /**
     * Sends the RPC payload over HTTP POST to the centralized management server.
     */
    private suspend fun sendRpcUpdate(track: TrackState, token: String) {
        _connectionStatus.value = ConnectionStatus.SENDING

        val activity = buildDiscordActivityPayload(track)
        val payload = RpcPayload(discordAccessToken = token, activity = activity)

        // The server needs the user's ID, which it will get by decoding the token,
        // so the endpoint is just the base status update path.
        val endpoint = "$API_BASE_URL/status/update"

        try {
            val response = client.post(endpoint) {
                contentType(ContentType.Application.Json)
                setBody(payload)
            }

            if (response.status.isSuccess()) {
                _connectionStatus.value = ConnectionStatus.SUCCESS
                Log.d("DiscordRpcService", "Status SENT successfully to $endpoint. Status: ${response.status}")
            } else {
                _connectionStatus.value = ConnectionStatus.ERROR
                Log.e("DiscordRpcService", "Failed to send payload. Server responded with: ${response.status}")
            }
        } catch (e: Exception) {
            _connectionStatus.value = ConnectionStatus.ERROR
            Log.e("DiscordRpcService", "Network/API Post error to $endpoint: ${e.message}", e)
        } finally {
            // Reset status after a short delay so user can see success/error state
            scope.launch {
                delay(2000)
                _connectionStatus.value = ConnectionStatus.READY
            }
        }
    }

    /**
     * Builds the internal representation of the Discord Activity payload.
     */
    private fun buildDiscordActivityPayload(track: TrackState): DiscordActivity {
        val currentTimeMs = System.currentTimeMillis()
        val startTime = track.calculateStartTimeMillis(currentTimeMs)
        val endTime = track.calculateEndTimeMillis(currentTimeMs)

        return DiscordActivity(
            details = if (track.isPlaying) "Listening to ${track.title}" else "Paused",
            state = if (track.isPlaying) "by ${track.artist} on Qobuz" else "Qobuz RPC Client",
            timestamps = DiscordTimestamps(
                start = startTime,
                end = endTime
            ),
            assets = DiscordAssets(
                largeImage = track.albumArtUrl ?: "qobuz_icon",
                largeText = track.album,
                smallImage = if (track.hiResQuality != null) "hi_res_icon" else "qobuz_icon",
                smallText = track.hiResQuality ?: "Standard Quality"
            )
        )
    }
}