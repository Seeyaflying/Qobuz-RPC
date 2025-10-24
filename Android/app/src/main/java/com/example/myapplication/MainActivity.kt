package com.example.myapplication

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.lifecycle.lifecycleScope
import com.example.myapplication.data.TrackState
import com.example.myapplication.network.DiscordAuthClient
import com.example.myapplication.service.ConnectionStatus
import com.example.myapplication.service.DiscordRpcService
import com.example.myapplication.ui.TrackDisplayCard
import com.example.myapplication.ui.theme.MyTheme
import kotlinx.coroutines.launch

/**
 * Main Activity for the Qobuz RPC client application, managing Discord Auth and RPC service.
 */
class MainActivity : ComponentActivity() {

    private lateinit var rpcService: DiscordRpcService
    private val authClient = DiscordAuthClient()

    // --- Discord OAuth Setup ---
    // !!! CRITICAL: REPLACE THESE PLACEHOLDERS !!!
    private val CLIENT_ID = "YOUR_DISCORD_CLIENT_ID"
    private val CLIENT_SECRET = "YOUR_DISCORD_CLIENT_SECRET"
    private val REDIRECT_URI = "qobuzrpc://callback"
    private val SCOPES = "activities.write" // Required for setting custom status

    // Mutable state for Discord Auth Token (Stored in rpcService.discordAccessToken)
    private var _isLoggedIn = mutableStateOf(false)
    val isLoggedIn: State<Boolean> = _isLoggedIn

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        rpcService = DiscordRpcService(applicationContext, lifecycleScope)

        setContent {
            MyTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    QobuzRpcScreen(
                        rpcService = rpcService,
                        isLoggedIn = isLoggedIn.value,
                        onLoginClick = { launchDiscordOAuth() }
                    )
                }
            }
        }

        handleIntent(intent)
    }

    // --- Handle the OAuth Redirect URI ---
    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_VIEW && intent.data != null) {
            val uri = intent.data
            if (uri.toString().startsWith(REDIRECT_URI)) {
                val code = uri?.getQueryParameter("code")
                if (code != null) {
                    // Exchange the 'code' for the 'access_token'
                    lifecycleScope.launch {
                        val tokenResponse = authClient.exchangeCodeForToken(
                            code, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI
                        )

                        if (tokenResponse != null) {
                            rpcService.discordAccessToken = tokenResponse.access_token
                            _isLoggedIn.value = true
                            Log.i("DiscordAuth", "Login SUCCESS. Token stored for RPC updates.")

                            // Optional: Immediately send a mock status after login
                            rpcService.updateTrackState(TrackState(title = "Initializing Status...", artist = "Qobuz RPC", isPlaying = true))

                        } else {
                            _isLoggedIn.value = false
                            Log.e("DiscordAuth", "Token exchange failed.")
                        }
                    }
                } else {
                    Log.e("DiscordAuth", "OAuth failed: No code received.")
                }
            }
        }
    }

    // --- Launch the OAuth Flow in the Browser ---
    private fun launchDiscordOAuth() {
        val authUrl = "https://discord.com/oauth2/authorize" +
                "?client_id=$CLIENT_ID" +
                "&redirect_uri=$REDIRECT_URI" +
                "&response_type=code" +
                "&scope=$SCOPES"

        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(authUrl))
        startActivity(intent)
    }
}

/**
 * The main composable screen for the Qobuz RPC application.
 */
@Composable
fun QobuzRpcScreen(rpcService: DiscordRpcService, isLoggedIn: Boolean, onLoginClick: () -> Unit) {
    val scope = rememberCoroutineScope()
    val trackState by rpcService.currentTrack.collectAsState()
    val sendStatus by rpcService.connectionStatus.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        // --- Discord Login/Status Card ---
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 8.dp),
            shape = MaterialTheme.shapes.medium
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Discord Status",
                    style = MaterialTheme.typography.titleLarge
                )
                Spacer(modifier = Modifier.height(8.dp))

                if (isLoggedIn) {
                    Text("✅ Logged in and Authorized.", color = MaterialTheme.colorScheme.primary)
                    Text("Token Ready for Status Updates.", style = MaterialTheme.typography.bodySmall)
                } else {
                    Text("❌ Not Logged In", color = MaterialTheme.colorScheme.error)
                    Button(onClick = onLoginClick, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                        Text("Authorize Discord Status (Login)")
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // --- Track Display Card ---
        TrackDisplayCard(trackState = trackState, modifier = Modifier.fillMaxWidth())

        Spacer(modifier = Modifier.height(32.dp))

        // --- RPC Test and API Status ---
        Text(text = "RPC Data Sender:", style = MaterialTheme.typography.titleLarge)
        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = {
                scope.launch {
                    val mockTrack = TrackState(
                        title = "Bohemian Rhapsody (Final Mix)",
                        artist = "Queen",
                        album = "A Night at the Opera",
                        isPlaying = true,
                        durationSeconds = 354,
                        positionSeconds = 120,
                        albumArtUrl = "https://i.imgur.com/G3Z2m8X.png",
                        hiResQuality = "24-bit / 96 kHz"
                    )
                    rpcService.updateTrackState(mockTrack)
                }
            },
            modifier = Modifier.fillMaxWidth(0.8f),
            enabled = isLoggedIn && sendStatus != ConnectionStatus.SENDING
        ) {
            Text("Send Playing Status")
        }

        Spacer(modifier = Modifier.height(16.dp))

        Button(
            onClick = {
                scope.launch {
                    rpcService.updateTrackState(TrackState(isPlaying = false))
                }
            },
            modifier = Modifier.fillMaxWidth(0.8f),
            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
            enabled = isLoggedIn && sendStatus != ConnectionStatus.SENDING
        ) {
            Text("Send Paused Status / Clear RPC")
        }

        Spacer(modifier = Modifier.height(24.dp))

        // API Send Status Display
        val (statusText, statusColor) = when (sendStatus) {
            ConnectionStatus.READY -> "Ready to send data" to MaterialTheme.colorScheme.onSurfaceVariant
            ConnectionStatus.SENDING -> "Sending update to Cloud API..." to MaterialTheme.colorScheme.primary
            ConnectionStatus.SUCCESS -> "Last Update SUCCESSFUL" to Color(0xFF4CAF50)
            ConnectionStatus.ERROR -> "Last Update FAILED" to MaterialTheme.colorScheme.error
            else -> "Offline" to MaterialTheme.colorScheme.onSurface
        }
        Text(
            text = "API Status: $statusText",
            color = statusColor,
            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold)
        )
    }
}