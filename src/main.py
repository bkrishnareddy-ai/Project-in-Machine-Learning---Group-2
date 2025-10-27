# src/main.py
from fastapi import FastAPI
from routers.reminder_router import router as reminder_router
from routers.dashboard_router import router as dashboard_router
from routers import profile_router 


app = FastAPI(
    title="MemoriAI Cognitive Service API",
    version="1.0",
    description="Cognitive Assist + Reminder + Dashboard Feed"
)

# Routers
app.include_router(reminder_router)
app.include_router(dashboard_router)
app.include_router(profile_router.router)

@app.get("/")
def healthcheck():
    return {"status": "ok", "service": "MemoriAI Cognitive Service"}
