import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const isPlayingRef = useRef(false);

  const playAudio = async (audioBlob, onEnd) => {
    setStatus("AI Agent speaking...");
    isPlayingRef.current = true;

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    const cleanup = () => {
      URL.revokeObjectURL(audioUrl);
    };

    audio.onended = () => {
      cleanup();
      isPlayingRef.current = false;
      if (onEnd) onEnd();
    };

    audio.onerror = (e) => {
      console.error("Audio playback error:", e);
      cleanup();
      isPlayingRef.current = false;
      setStatus("Error playing audio");
    };

    try {
      await audio.play();
    } catch (err) {
      console.error("Autoplay blocked or failed:", err);
      cleanup();
      isPlayingRef.current = false;
      setStatus("Autoplay blocked. Please interact and try again.");
    }
  };

  // Start a new session and play greeting (frontend TTS removed)
  const startCall = async () => {
    setStatus("Starting session...");
    try {
      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

      // Instead of speaking greeting, we immediately start listening.
      // (Keeping session logic the same; only /message returns audio now.)
      setStatus("Listening...");
      startRecognition(newSessionId);
    } catch (err) {
      console.error("Failed to start session:", err);
      setStatus("Error starting session");
    }
  };

  // Start listening for user voice
  const startRecognition = (sessionId) => {
    if (isPlayingRef.current) return;

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

      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);

      silenceTimerRef.current = setTimeout(async () => {
        recognition.stop();
        setStatus("Processing your message...");

        try {
          const response = await fetch("http://127.0.0.1:8000/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: sessionId,
              user_message: transcript,
            }),
          });

          const audioBlob = await response.blob();

          playAudio(audioBlob, () => {
            setStatus("Listening...");
            startRecognition(sessionId);
          });
        } catch (err) {
          console.error("Failed to send message:", err);
          setStatus("Error processing message");
        }
      }, 3000);
    };

    recognition.onerror = (event) => {
      console.error("Recognition error:", event.error);
      setStatus("Error in recognition");
    };

    recognition.onend = () => {
      if (status === "Listening..." && !isPlayingRef.current) recognition.start();
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
