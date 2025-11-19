import { useState } from "react";

export default function PDFUpload({ deckId, flashcards, setFlashcards }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://localhost:8000/generate_flashcards", {
      method: "POST",
      body: formData,
    });

    const data = await res.json();
    const generated = data.flashcards || [];

    for (const card of generated) {
      const createRes = await fetch(
        `http://localhost:8000/decks/${deckId}/flashcards/`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question: card.question,
            answer: card.answer,
          }),
        }
      );
      const created = await createRes.json();
      setFlashcards((prev) => [...prev, created]);
    }

    setLoading(false);
    setFile(null);
  };

  return (
    <div className="flex items-center gap-3 mb-6">
      <input
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files[0])}
        className="bg-gray-800 p-2 rounded"
      />
      <button
        onClick={handleUpload}
        disabled={loading}
        className="bg-purple-600 px-4 py-2 rounded"
      >
        {loading ? "Processing..." : "Upload PDF"}
      </button>
    </div>
  );
}
