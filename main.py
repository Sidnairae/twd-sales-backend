from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import traceback

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

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"Unhandled error on {request.method} {request.url}:\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {str(exc)}"},
    )

app.include_router(auth.router,         prefix="/api", tags=["auth"])
app.include_router(projects.router,     prefix="/api", tags=["projects"])
app.include_router(import_data.router,  prefix="/api", tags=["import"])
app.include_router(contacts.router,     prefix="/api", tags=["contacts"])
app.include_router(favorites.router,    prefix="/api", tags=["favorites"])
app.include_router(sync_scores.router,  prefix="/api", tags=["sync"])
app.include_router(summarize.router,    prefix="/api", tags=["summarize"])
app.include_router(meeting_prep.router, prefix="/api", tags=["meeting_prep"])
app.include_router(research.router,     prefix="/api", tags=["research"])
app.include_router(clear.router,        prefix="/api", tags=["clear"])

@app.get("/health")
def health():
    return {"status": "ok"}
