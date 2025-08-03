# app/api/ask.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/")
def ask_question():
    return {"message": "Ask endpoint will be implemented here."}
