package com.example.myapplication.network

import android.util.Log
import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.engine.android.*
import io.ktor.client.plugins.contentnegotiation.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import io.ktor.http.*
import io.ktor.serialization.kotlinx.json.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * Client for handling Discord OAuth2 token exchange and API calls.
 */
class DiscordAuthClient {
    private val client = HttpClient(Android) {
        install(ContentNegotiation) {
            json(Json { ignoreUnknownKeys = true })
        }
    }

    private val tokenUrl = "https://discord.com/api/oauth2/token"

    /**
     * Data received from Discord after successful token exchange.
     */
    @Serializable
    data class TokenResponse(
        val access_token: String,
        val token_type: String,
        val expires_in: Int,
        val refresh_token: String? = null,
        val scope: String
    )

    /**
     * Exchanges the authorization code for an access token.
     */
    suspend fun exchangeCodeForToken(
        code: String,
        clientId: String,
        clientSecret: String,
        redirectUri: String
    ): TokenResponse? {
        try {
            val response: HttpResponse = client.post(tokenUrl) {
                contentType(ContentType.Application.FormUrlEncoded)
                setBody(
                    "client_id=$clientId" +
                            "&client_secret=$clientSecret" +
                            "&grant_type=authorization_code" +
                            "&code=$code" +
                            "&redirect_uri=$redirectUri"
                )
            }

            if (response.status.isSuccess()) {
                Log.i("DiscordAuthClient", "Token exchange successful.")
                return response.body<TokenResponse>()
            } else {
                val errorBody = response.bodyAsText()
                Log.e("DiscordAuthClient", "Token exchange failed: ${response.status} - $errorBody")
                return null
            }
        } catch (e: Exception) {
            Log.e("DiscordAuthClient", "Network error during token exchange: ${e.message}", e)
            return null
        }
    }
}