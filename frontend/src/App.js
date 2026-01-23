import React, { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const isListeningRef = useRef(false);

  const playWavResponse = async (response) => {
    const buf = await response.arrayBuffer();
    const blob = new Blob([buf], { type: "audio/wav" });
    const url = URL.createObjectURL(blob);

    return new Promise((resolve, reject) => {
      const audio = new Audio(url);
      audio.onended = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.onerror = (e) => {
        URL.revokeObjectURL(url);
        reject(e);
      };
      audio.play().catch(reject);
    });
  };

  const stopRecognition = () => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      } catch (e) {}
      recognitionRef.current = null;
    }
    isListeningRef.current = false;
  };

  const startCall = async () => {
    setStatus("Starting session...");
    stopRecognition();
    try {
      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      const newSessionId = data.session_id;
      const greeting = data.greeting || "BelMedic. Ana speaking. How can I help?";

      setSessionId(newSessionId);
      setMessages([{ role: "assistant", text: greeting }]);
      
      setStatus("Listening...");
      startRecognition(newSessionId);
    } catch (err) {
      console.error("Failed to start session:", err);
      setStatus("Error starting session");
    }
  };

  const startRecognition = (sId) => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
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
        const finalText = transcript.trim();
        if (!finalText) return;

        stopRecognition();
        setStatus("Processing...");
        setMessages((prev) => [...prev, { role: "user", text: finalText }]);

        try {
          const response = await fetch("http://127.0.0.1:8000/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sId, user_message: finalText }),
          });

          if (!response.ok) throw new Error(`HTTP ${response.status}`);

          const responseText = response.headers.get("X-Response-Text") || "";
          if (responseText) {
            setMessages((prev) => [...prev, { role: "assistant", text: responseText }]);
          }

          await playWavResponse(response);
          
          setStatus("Listening...");
          startRecognition(sId);
        } catch (err) {
          console.error("Error:", err);
          setStatus("Error processing message");
        }
      }, 3000);
    };

    recognition.onend = () => {
      if (isListeningRef.current) {
        try { recognition.start(); } catch (e) {}
      }
    };

    recognition.start();
    recognitionRef.current = recognition;
    isListeningRef.current = true;
  };

  useEffect(() => {
    return () => stopRecognition();
  }, []);

  return (
    <div className="app">
      <h1>AI Medical Agent</h1>
      <p>{status}</p>
      <button onClick={startCall} className="call-button">Call AI</button>
      <div className="chat">
        {messages.map((m, idx) => (
          <div key={idx} className={`msg ${m.role}`}>
            <strong>{m.role === "assistant" ? "Ana" : "You"}:</strong> {m.text}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
