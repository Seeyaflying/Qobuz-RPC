package com.example.helloworld

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

// MainActivity is the class responsible for managing the main screen/layout
class MainActivity : AppCompatActivity() {

    // The onCreate function is the first function called when the Activity is created
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Links the Kotlin code to the XML layout (activity_main.xml)
        setContentView(R.layout.activity_main)

        // 1. Get references to the UI elements using their IDs
        val greetingTextView: TextView = findViewById(R.id.greetingTextView)
        val nameEditText: EditText = findViewById(R.id.nameEditText)
        val sayHelloButton: Button = findViewById(R.id.sayHelloButton)

        // 2. Set the action to perform when the button is clicked
        sayHelloButton.setOnClickListener {

            // Read the text the user typed into the input field
            val enteredName = nameEditText.text.toString().trim()

            // Check if the user entered a name
            if (enteredName.isNotEmpty()) {
                // If a name is entered, create a personalized greeting
                val personalizedGreeting = "Hello, $enteredName! Welcome to Android."
                // Update the TextView with the new message
                greetingTextView.text = personalizedGreeting
            } else {
                // If no name is entered, prompt the user
                greetingTextView.text = "Please enter your name above!"
            }
        }
    }
}