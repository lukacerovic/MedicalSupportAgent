import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);

  // Play WAV bytes returned by backend
  const playWavResponse = async (response) => {
    const buf = await response.arrayBuffer();
    const blob = new Blob([buf], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);

    const audio = new Audio(url);
    audio.onended = () => URL.revokeObjectURL(url);

    await audio.play();
  };

  // Start a new session and play greeting
  const startCall = async () => {
    setStatus("Starting session...");
    try {
      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

      // If backend sends audio greeting in the future, we can play it here.
      // For now, just start listening.
      setStatus("Listening...");
      startRecognition(newSessionId);
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

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }

          // Transcript is sent via header, WAV is the response body
          const responseText = response.headers.get("X-Response-Text") || "";
          if (responseText) {
            console.log("AI:", responseText);
          }

          // Auto-play the wav returned by backend
          await playWavResponse(response);

          setStatus("Listening...");
          startRecognition(sessionId); // continue listening
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
