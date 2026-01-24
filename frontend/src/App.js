import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);

  // Keep this flag so we don't re-enter listening while audio is playing
  const isPlayingAudioRef = useRef(false);

  // Greeting uses browser TTS exactly like before
  const speakGreeting = (text, onEnd) => {
    setStatus("AI Agent speaking...");
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.onend = () => {
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(utterance);
  };

  // AI response uses backend audio
  const playResponseAudio = async (audioBlob, onEnd) => {
    setStatus("AI Agent speaking...");
    isPlayingAudioRef.current = true;

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    const cleanup = () => {
      URL.revokeObjectURL(audioUrl);
    };

    audio.onended = () => {
      cleanup();
      isPlayingAudioRef.current = false;
      if (onEnd) onEnd();
    };

    audio.onerror = (e) => {
      console.error("Audio playback error:", e);
      cleanup();
      isPlayingAudioRef.current = false;
      setStatus("Error playing audio");
    };

    try {
      await audio.play();
    } catch (err) {
      console.error("Autoplay blocked or failed:", err);
      cleanup();
      isPlayingAudioRef.current = false;
      setStatus("Autoplay blocked. Please interact and try again.");
    }
  };

  // Start a new session and speak greeting
  const startCall = async () => {
    setStatus("Starting session...");
    try {
      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

      // Speak greeting using browser TTS (kept)
      speakGreeting(data.greeting, () => {
        setStatus("Listening...");
        startRecognition(newSessionId);
      });
    } catch (err) {
      console.error("Failed to start session:", err);
      setStatus("Error starting session");
    }
  };

  // Start listening for user voice (pause detection logic unchanged)
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
            const errText = await response.text();
            throw new Error(errText);
          }

          const audioBlob = await response.blob();

          // Play AI response audio from backend
          playResponseAudio(audioBlob, () => {
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
      // Restart recognition only if we are in listening mode and NOT playing audio.
      if (status === "Listening..." && !isPlayingAudioRef.current) recognition.start();
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
