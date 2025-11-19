import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import FlashCard from "./FlashCard";
import DeckReview from "./DeckReview";
import PDFUpload from "./Pdf";
import Chatbot from "./Chatbot";

export default function DeckDetail() {
  const { deckId } = useParams();
  const [flashcards, setFlashcards] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [reviewMode, setReviewMode] = useState(false);

  useEffect(() => {
    fetch(`http://localhost:8000/decks/${deckId}/flashcards/`)
      .then((res) => res.json())
      .then(setFlashcards);
  }, [deckId]);

  const addFlashcard = async () => {
    const res = await fetch(
      `http://localhost:8000/decks/${deckId}/flashcards/`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, answer }),
      },
    );
    const data = await res.json();
    setFlashcards([...flashcards, data]);
    setQuestion("");
    setAnswer("");
  };

  if (reviewMode)
    return (
      <div className="w-full min-h-screen flex flex-col p-6">
        <div className="flex justify-between mb-6">
          <h1 className="text-2xl font-semibold">Review Deck {deckId}</h1>
          <button
            onClick={() => setReviewMode(false)}
            className="bg-gray-700 px-4 py-2 rounded"
          >
            Back
          </button>
        </div>
        <DeckReview flashcards={flashcards} />
      </div>
    );

    return (
  <div className="p-6 flex gap-6">
    <div className="flex-1">
      <div className="flex justify-between mb-6">
        <h1 className="text-2xl font-semibold">Deck {deckId}</h1>
        <button
          onClick={() => setReviewMode(true)}
          className="bg-blue-600 px-4 py-2 rounded"
        >
          Start Review
        </button>
      </div>

      <PDFUpload
        deckId={deckId}
        flashcards={flashcards}
        setFlashcards={setFlashcards}
      />

      <div className="flex gap-2 mb-6">
        <input
          className="p-2 rounded bg-gray-800 flex-1"
          placeholder="Question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <input
          className="p-2 rounded bg-gray-800 flex-1"
          placeholder="Answer"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
        />
        <button
          onClick={addFlashcard}
          className="bg-green-600 px-4 py-2 rounded"
        >
          Add
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-6">
        {flashcards.map((card) => (
          <div key={card.card_id} className="w-full">
            <FlashCard question={card.question} answer={card.answer} />
          </div>
        ))}
      </div>
    </div>

    <div className="h-screen">
      <Chatbot />
    </div>
  </div>
);

}
