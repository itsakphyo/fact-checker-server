from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.fact_check import router as fact_check_router
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

app.include_router(fact_check_router)

@app.get("/")
async def root():
    return {"message": "Server is running!"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)