import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const isPlayingRef = useRef(false);

  // Keep one audio element alive for the whole session. This helps with autoplay policies.
  const audioRef = useRef(null);

  const ensureAudioElement = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = "auto";
    }
    return audioRef.current;
  };

  // Unlock audio playback during a user gesture (Call AI click).
  const unlockAudio = async () => {
    try {
      const audio = ensureAudioElement();
      // Attempt a play/pause cycle to get autoplay permission.
      // Some browsers require a user gesture before any audio can be played later.
      audio.src = "";
      await audio.play();
      audio.pause();
    } catch (e) {
      // If this fails, we will still try to play later, and fall back to prompting the user.
      console.warn("Audio unlock failed (may still be OK):", e);
    }
  };

  const playAudio = async (audioBlob, onEnd) => {
    setStatus("AI Agent speaking...");
    isPlayingRef.current = true;

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = ensureAudioElement();

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

    audio.src = audioUrl;

    try {
      await audio.play();
    } catch (err) {
      console.error("Autoplay blocked or failed:", err);
      cleanup();
      isPlayingRef.current = false;
      setStatus("Autoplay blocked. Click 'Call AI' again to enable sound.");
    }
  };

  // Start a new session (kept same JSON contract)
  const startCall = async () => {
    setStatus("Starting session...");
    try {
      // Ensure this runs inside the click handler user gesture.
      await unlockAudio();

      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

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
