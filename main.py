from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.routers import projects, import_data, contacts, favorites, sync_scores, summarize, meeting_prep, research, clear, auth

app = FastAPI(title="TWD Sales Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router,     prefix="/api", tags=["projects"])
app.include_router(import_data.router,  prefix="/api", tags=["import"])
app.include_router(contacts.router,     prefix="/api", tags=["contacts"])
app.include_router(favorites.router,    prefix="/api", tags=["favorites"])
app.include_router(sync_scores.router,  prefix="/api", tags=["sync"])
app.include_router(summarize.router,    prefix="/api", tags=["summarize"])
app.include_router(meeting_prep.router, prefix="/api", tags=["meeting_prep"])
app.include_router(research.router,     prefix="/api", tags=["research"])
app.include_router(clear.router,        prefix="/api", tags=["clear"])
app.include_router(auth.router,         prefix="/api", tags=["auth"])

@app.get("/health")
def health():
    return {"status": "ok"}
