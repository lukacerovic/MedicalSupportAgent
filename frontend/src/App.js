import React, { useState, useRef } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Click 'Call AI' to start");
  const [sessionId, setSessionId] = useState(null);
  const recognitionRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const isPlayingAudioRef = useRef(false);

  // AudioContext for streaming playback
  const audioCtxRef = useRef(null);
  // Track when the next chunk should play
  const nextStartTimeRef = useRef(0);

  // Ensure AudioContext is ready (browser requirement)
  const getAudioContext = () => {
    if (!audioCtxRef.current) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioCtxRef.current = new AudioContext();
    }
    if (audioCtxRef.current.state === "suspended") {
      audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  };

  const speakGreeting = (text, onEnd) => {
    setStatus("AI Agent speaking...");
    isPlayingAudioRef.current = true;
    
    // Stop recognition if it's running
    if (recognitionRef.current) recognitionRef.current.stop();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.onend = () => {
      isPlayingAudioRef.current = false;
      if (onEnd) onEnd();
    };
    window.speechSynthesis.speak(utterance);
  };

  const playStreamResponse = async (response, onEnd) => {
    setStatus("AI Agent speaking...");
    isPlayingAudioRef.current = true;
    
    if (recognitionRef.current) recognitionRef.current.stop();

    const ctx = getAudioContext();
    const reader = response.body.getReader();
    
    // Sync start time
    nextStartTimeRef.current = ctx.currentTime;

    // Buffer for "leftover" bytes if chunk is not multiple of 2
    let leftover = new Uint8Array(0);

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // Combine leftover with new data
        const input = new Uint8Array(leftover.length + value.length);
        input.set(leftover);
        input.set(value, leftover.length);

        // We need even number of bytes for Int16
        const remainder = input.length % 2;
        const validLength = input.length - remainder;
        
        const chunkData = input.subarray(0, validLength);
        leftover = input.subarray(validLength);

        if (chunkData.length > 0) {
          // Convert Int16 (bytes) -> Float32
          const int16 = new Int16Array(chunkData.buffer, chunkData.byteOffset, chunkData.length / 2);
          const float32 = new Float32Array(int16.length);
          for (let i = 0; i < int16.length; i++) {
            // Scale Int16 to Float32 range [-1.0, 1.0]
            float32[i] = int16[i] / 32768.0;
          }

          // Create AudioBuffer (Piper is 22050Hz, 1ch)
          const audioBuffer = ctx.createBuffer(1, float32.length, 22050);
          audioBuffer.getChannelData(0).set(float32);

          const source = ctx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(ctx.destination);

          // Schedule playback
          // Ensure we don't schedule in the past
          if (nextStartTimeRef.current < ctx.currentTime) {
             nextStartTimeRef.current = ctx.currentTime;
          }
          
          source.start(nextStartTimeRef.current);
          nextStartTimeRef.current += audioBuffer.duration;
        }
      }
    } catch (err) {
      console.error("Stream reading error:", err);
    }

    // Wait for the final audio to finish playing
    // We calculate when the last scheduled chunk ends
    const delay = (nextStartTimeRef.current - ctx.currentTime) * 1000;
    
    setTimeout(() => {
        isPlayingAudioRef.current = false;
        if (onEnd) onEnd();
    }, Math.max(0, delay));
  };

  const startCall = async () => {
    setStatus("Starting session...");
    try {
      const res = await fetch("http://127.0.0.1:8000/start_session");
      const data = await res.json();
      setSessionId(data.session_id);

      speakGreeting(data.greeting, () => {
        setStatus("Listening...");
        startRecognition(data.session_id);
      });
    } catch (err) {
      console.error("Failed to start session:", err);
      setStatus("Error starting session");
    }
  };

  const startRecognition = (sid) => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Browser not supported");
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
        setStatus("Processing...");

        try {
          const response = await fetch("http://127.0.0.1:8000/message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              session_id: sid,
              user_message: transcript,
            }),
          });

          if (!response.ok) throw new Error("Network response was not ok");
          
          // Use the new streaming player
          await playStreamResponse(response, () => {
             setStatus("Listening...");
             // Only restart if we are not already recording (safety check)
             startRecognition(sid);
          });

        } catch (err) {
          console.error("Error:", err);
          setStatus("Error processing message");
          // Retry listening on error
          setTimeout(() => startRecognition(sid), 2000);
        }
      }, 2000); // Reduced silence wait to 2s for snappier feel
    };

    recognition.onerror = (event) => {
       console.error("Rec error:", event.error);
       // Ignore "no-speech" errors which happen frequently
       if (event.error !== 'no-speech') {
           setStatus("Error: " + event.error);
       }
    };

    recognition.start();
    recognitionRef.current = recognition;
  };

  return (
    <div className="app">
      <h1>AI Medical Agent (Streaming)</h1>
      <p>{status}</p>
      <button onClick={startCall} className="call-button">
        Call AI
      </button>
    </div>
  );
}

export default App;
