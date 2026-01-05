import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);

  // Function to speak text via native TTS
  const speak = (text, onEnd) => {
    setStatus("AI Agent speaking...");
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.onend = () => {
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(utterance);
  };

  // Start a new session and play greeting
  const startCall = async () => {
    setStatus("Starting session...");
    try {
      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

      // Play greeting using TTS
      speak(data.greeting, () => {
        setStatus("Listening...");
        startRecognition(newSessionId);
      });
    } catch (err) {
      console.error("Failed to start session:", err);
      setStatus("Error starting session");
    }
  };

  // Start listening for user voice
  const startRecognition = (sessionId) => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Your browser does not support Speech Recognition");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;

    let transcript = "";

    recognition.onresult = (event) => {
      transcript = "";
      for (let i = 0; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }

      // Reset silence timer on any speech
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

      // Set timer to detect 3s silence
      silenceTimerRef.current = setTimeout(async () => {
        recognition.stop(); // stop recording

        setStatus("Processing your message...");

        // Send transcript to backend
        try {
          const response = await fetch("http://127.0.0.1:8000/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: sessionId,
              user_message: transcript,
            }),
          });
          const data = await response.json();

          // Play AI response
          speak(data.response, () => {
            setStatus("Listening...");
            startRecognition(sessionId); // continue listening
          });
        } catch (err) {
          console.error("Failed to send message:", err);
          setStatus("Error processing message");
        }
      }, 3000); // 3s pause
    };

    recognition.onerror = (event) => {
      console.error("Recognition error:", event.error);
      setStatus("Error in recognition");
    };

    recognition.onend = () => {
      // This triggers if recognition stops without silence timer
      if (status === "Listening...") recognition.start();
    };

    recognition.start();
    recognitionRef.current = recognition;
  };

  return (
    <div className="app">
      <h1>AI Medical Agent</h1>
      <p>{status}</p>
      <button onClick={startCall} className="call-button">
        Call AI
      </button>
    </div>
  );
}

export default App;
