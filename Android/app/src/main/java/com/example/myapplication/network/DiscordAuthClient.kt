package com.example.myapplication.network

import android.util.Log
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.android.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.forms.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Data class to hold the successful response from Discord's OAuth2 token endpoint.
 */
@Serializable
data class DiscordTokenResponse(
    val access_token: String,
    val token_type: String,
    val expires_in: Int,
    val refresh_token: String,
    val scope: String
)

/**
 * A Ktor HTTP client specifically for handling the Discord OAuth2 token exchange.
 */
class DiscordAuthClient {

    // Configure the Ktor HTTP client
    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true // Important for handling responses from Discord
            })
        }
    }

    private val TOKEN_ENDPOINT = "https://discord.com/api/v10/oauth2/token"

    /**
     * Exchanges an authorization code for an access token from Discord's API.
     *
     * @return A [DiscordTokenResponse] on success, or null on failure.
     */
    suspend fun exchangeCodeForToken(
        code: String,
        clientId: String,
        clientSecret: String,
        redirectUri: String
    ): DiscordTokenResponse? {
        return try {
            val response: HttpResponse = client.submitForm(
                url = TOKEN_ENDPOINT,
                // FIX: Use `parameters` to send data as 'application/x-www-form-urlencoded'
                formParameters = parameters {
                    append("client_id", clientId)
                    append("client_secret", clientSecret)
                    append("grant_type", "authorization_code")
                    append("code", code)
                    append("redirect_uri", redirectUri)
                }
            )

            if (response.status.isSuccess()) {
                Log.i("DiscordAuthClient", "Successfully exchanged code for token.")
                response.body<DiscordTokenResponse>()
            } else {
                val errorBody = response.bodyAsText()
                Log.e(
                    "DiscordAuthClient",
                    "Token exchange failed with status ${response.status}: $errorBody"
                )
                null
            }
        } catch (e: Exception) {
            Log.e("DiscordAuthClient", "Exception during token exchange", e)
            null
        }
    }
}
