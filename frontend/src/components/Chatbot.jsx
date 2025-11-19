import { useState, useRef, useEffect } from "react";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { role: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chatbot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: userMessage.text }),
      });

      const data = await res.json();
      const botMessage = { role: "assistant", text: data.response };

      setMessages((prev) => [...prev, botMessage]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Error connecting to chatbot." },
      ]);
    }

    setLoading(false);
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-[80vh] bg-gray-900 rounded p-4 border border-gray-700">
      <div className="text-xl font-semibold mb-3">Chatbot</div>

      <div className="flex-1 overflow-y-auto pr-2 space-y-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`p-3 rounded max-w-xs ${
              m.role === "user" ? "bg-blue-700 ml-auto" : "bg-gray-700 mr-auto"
            }`}
          >
            {m.text}
          </div>
        ))}
        <div ref={bottomRef}></div>
      </div>

      <div className="flex gap-2 mt-4">
        <input
          className="flex-1 p-2 rounded bg-gray-800"
          placeholder="Ask something..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button
          onClick={sendMessage}
          disabled={loading}
          className="bg-purple-600 px-4 py-2 rounded"
        >
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}
