from fastapi import FastAPI, Depends, HTTPException, Path, Body,UploadFile, File
from pypdf import PdfReader
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import ollama
import uvicorn
import io

DATABASE_URL = "sqlite:///./flashcards.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ---------------------
# Database Models
# ---------------------

class Deck(Base):
    __tablename__ = "decks"
    deck_id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    flashcards = relationship("Flashcard", back_populates="deck", cascade="all, delete")


class Flashcard(Base):
    __tablename__ = "flashcards"
    card_id = Column(Integer, primary_key=True, index=True)
    deck_id = Column(Integer, ForeignKey("decks.deck_id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    mnemonic = Column(Text)
    is_ai_generated = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    deck = relationship("Deck", back_populates="flashcards")


# ---------------------
# Pydantic Schemas
# ---------------------
class FlashcardBase(BaseModel):
    question: str
    answer: str
    mnemonic: str | None = None
    is_ai_generated: int | None = 0


class FlashcardCreate(FlashcardBase):
    pass


class FlashcardRead(FlashcardBase):
    card_id: int
    deck_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


# ---------------------
# FastAPI setup
# ---------------------
app = FastAPI(title="Smart Study Flashcards API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------
# CRUD Endpoints
# ---------------------

@app.post("/decks/", response_model=dict)
def create_deck(deck: dict = Body(...), db: Session = Depends(get_db)):
    new_deck = Deck(**deck)
    db.add(new_deck)
    db.commit()
    db.refresh(new_deck)
    return {"deck_id": new_deck.deck_id, "title": new_deck.title, "description": new_deck.description}

@app.get("/decks/", response_model=list[dict])
def get_decks(db: Session = Depends(get_db)):
    decks = db.query(Deck).all()
    return [{"deck_id": d.deck_id, "title": d.title, "description": d.description} for d in decks]


@app.post("/decks/{deck_id}/flashcards/", response_model=FlashcardRead)
def create_flashcard(deck_id: int, flashcard: FlashcardCreate, db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.deck_id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    new_card = Flashcard(deck_id=deck_id, **flashcard.dict())
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card


@app.get("/decks/{deck_id}/flashcards/", response_model=list[FlashcardRead])
def get_flashcards(deck_id: int, db: Session = Depends(get_db)):
    cards = db.query(Flashcard).filter(Flashcard.deck_id == deck_id).all()
    return cards


@app.get("/flashcards/{card_id}", response_model=FlashcardRead)
def get_flashcard(card_id: int = Path(...), db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.card_id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    return card


@app.put("/flashcards/{card_id}", response_model=FlashcardRead)
def update_flashcard(card_id: int, flashcard: FlashcardBase, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.card_id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    for key, value in flashcard.dict(exclude_unset=True).items():
        setattr(card, key, value)
    db.commit()
    db.refresh(card)
    return card


@app.delete("/flashcards/{card_id}")
def delete_flashcard(card_id: int, db: Session = Depends(get_db)):
    card = db.query(Flashcard).filter(Flashcard.card_id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    db.delete(card)
    db.commit()
    return {"detail": "Flashcard deleted successfully"}


@app.post("/generate_flashcards")
async def generate_flashcards(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Upload a PDF.")

    content = await file.read()
    reader = PdfReader(io.BytesIO(content))

    pages = []
    for page in reader.pages:
        t = page.extract_text()
        if t and t.strip():
            pages.append(t.strip())

    if not pages:
        raise HTTPException(status_code=400, detail="PDF contains no readable text.")

    full_text = " ".join(pages)
    words = full_text.split()
    chunks = [" ".join(words[i:i+100]) for i in range(0, len(words), 100)]

    all_flashcards = []

    for chunk in chunks:
        instruction = """
You generate flashcards from the given text.

Requirements:
- Use only information contained in the text.
- Create concise flashcards.
- Each flashcard must have:
    question
    answer
    mnemonic (optional)
- No commentary or explanations.
- Output strictly in this JSON format:

{
    "flashcards": [
        {
        "question": "...",
        "answer": "...",
        "mnemonic": "..."
        }
    ]
}

Text:
<<<START>>>
{content}
<<<END>>>
""".replace("{content}", chunk)

        result = ollama.generate(
            model="llama3.2",
            prompt=instruction,
            format="json",
        )

        raw = result["response"].strip()

        try:
            parsed = json.loads(raw)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Flashcard model returned invalid JSON: {e}"
            )

        all_flashcards.extend(parsed.get("flashcards", []))

    # Filter invalid cards before returning
    cleaned = []
    for c in all_flashcards:
        q = c.get("question", "").strip()
        a = c.get("answer", "").strip()
        if q and a:
            cleaned.append({"question": q, "answer": a})

    return {"flashcards": cleaned}



@app.post("/chatbot")
async def chatbot(prompt: str = Body(..., embed=True)):
    instruction = """
You are a friendly chatbot and will answer the user's question briefly.
Output strictly in this JSON format:

{
    "response": "..."
}

Text:
<<<START>>>
{user_prompt}
<<<END>>>
""".replace("{user_prompt}", prompt)

    result = ollama.generate(
        model="llama3.2",
        prompt=instruction,
        format="json",
    )

    raw = result.get("response", "").strip()

    try:
        parsed = json.loads(raw)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Model returned invalid JSON"
        )

    return {"response": parsed.get("response", "")}


if __name__ == "__main__":
    uvicorn.run(app)
