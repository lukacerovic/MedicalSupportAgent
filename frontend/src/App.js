import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const [pendingAudioUrl, setPendingAudioUrl] = useState(null);

  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const isPlayingRef = useRef(false);

  const audioRef = useRef(null);

  const ensureAudioElement = () => {
    if (!audioRef.current) {
      audioRef.current = new Audio();
      audioRef.current.preload = "auto";
    }
    return audioRef.current;
  };

  const cleanupPending = () => {
    if (pendingAudioUrl) URL.revokeObjectURL(pendingAudioUrl);
    setPendingAudioUrl(null);
  };

  const playUrl = async (audioUrl, onEnd) => {
    setStatus("AI Agent speaking...");
    isPlayingRef.current = true;

    const audio = ensureAudioElement();

    audio.onended = () => {
      isPlayingRef.current = false;
      if (onEnd) onEnd();
    };

    audio.onerror = (e) => {
      console.error("Audio playback error:", e);
      isPlayingRef.current = false;
      setStatus("Error playing audio");
    };

    audio.src = audioUrl;

    try {
      await audio.play();
      // If play succeeded, clear any pending audio.
      cleanupPending();
    } catch (err) {
      console.error("Autoplay blocked or failed:", err);
      isPlayingRef.current = false;
      setStatus("Click 'Play response' to hear the AI.");
      setPendingAudioUrl(audioUrl);
    }
  };

  const playBlob = async (audioBlob, onEnd) => {
    const audioUrl = URL.createObjectURL(audioBlob);
    await playUrl(audioUrl, () => {
      URL.revokeObjectURL(audioUrl);
      if (onEnd) onEnd();
    });
  };

  const startCall = async () => {
    setStatus("Starting session...");
    try {
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

          if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText);
          }

          const audioBlob = await response.blob();
          await playBlob(audioBlob, () => {
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

  const onPlayPending = async () => {
    if (!pendingAudioUrl) return;
    await playUrl(pendingAudioUrl, () => {
      setStatus("Listening...");
      if (sessionId) startRecognition(sessionId);
    });
  };

  return (
    <div className="app">
      <h1>AI Medical Agent</h1>
      <p>{status}</p>
      <button onClick={startCall} className="call-button">
        Call AI
      </button>

      {pendingAudioUrl && (
        <button onClick={onPlayPending} className="call-button">
          Play response
        </button>
      )}
    </div>
  );
}

export default App;
