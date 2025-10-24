package com.example.myapplication.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.* // This already includes Card, CardDefaults, etc.
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.myapplication.data.TrackState

/**
 * A composable card to display the current track information in a stylish way.
 */
@Composable
fun TrackDisplayCard(trackState: TrackState, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.height(IntrinsicSize.Min),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(
            // This line will work once MyTheme.kt is corrected.
            containerColor = MaterialTheme.colorScheme.surfaceContainerHigh
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Album Art
            AsyncImage(
                model = trackState.albumArtUrl,
                contentDescription = "Album Art for ${trackState.album}",
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(96.dp)
                    .clip(RoundedCornerShape(8.dp)) // No need for the full path here
                    .background(MaterialTheme.colorScheme.primaryContainer)
            )

            Spacer(modifier = Modifier.width(16.dp))

            // Text Details Column
            Column(modifier = Modifier.weight(1f)) {
                // Hi-Res Badge
                if (trackState.hiResQuality != null) {
                    HiResBadge(quality = trackState.hiResQuality)
                    Spacer(modifier = Modifier.height(4.dp))
                }

                // Title
                Text(
                    text = trackState.title,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurface
                )
                // Artist
                Text(
                    text = trackState.artist,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                // Album
                Text(
                    text = trackState.album,
                    style = MaterialTheme.typography.bodySmall,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Playback Status (Simple text placeholder)
                val statusText = if (trackState.isPlaying) "• Playing" else "• Paused"
                Text(
                    text = statusText,
                    style = MaterialTheme.typography.labelSmall,
                    color = if (trackState.isPlaying) Color(0xFF4CAF50) else MaterialTheme.colorScheme.error
                )
            }
        }

        // Progress Bar
        val progress = if (trackState.durationSeconds > 0) {
            trackState.positionSeconds.toFloat() / trackState.durationSeconds.toFloat()
        } else {
            0f
        }

        LinearProgressIndicator(
            progress = progress,
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.primary
        )
    }
}

@Composable
fun HiResBadge(quality: String) {
    Surface(
        color = MaterialTheme.colorScheme.secondaryContainer,
        shape = RoundedCornerShape(4.dp),
        modifier = Modifier.padding(bottom = 2.dp)
    ) {
        Text(
            text = "HI-RES",
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Black),
            color = MaterialTheme.colorScheme.onSecondaryContainer,
            modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
        )
    }
}
