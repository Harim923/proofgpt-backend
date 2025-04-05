from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
import os, time
from collections import defaultdict

load_dotenv()
app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# IP별 호출 기록 저장 (하루 10회 제한)
request_log = defaultdict(list)
RATE_LIMIT = 10

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    ip = request.client.host
    now = time.time()
    request_log[ip] = [t for t in request_log[ip] if now - t < 86400]
    if len(request_log[ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again tomorrow.")
    request_log[ip].append(now)
    return await call_next(request)

@app.post("/api/proof")
async def get_proof(req: Request):
    body = await req.json()
    problem = body.get("problem", "").strip()
    axiomSet = body.get("axiomSet", "").lower()

    # 예시용 Axiom
    axioms = [
        "Axiom 1: Any two distinct points determine a unique line.",
        "Axiom 2: There exists at least three non-collinear points."
    ] if axiomSet == "hilbert" else [
        "Axiom A: Placeholder axiom for Euclid",
        "Axiom B: Placeholder axiom for Tarski"
    ]

    prompt = build_prompt(problem, axioms)

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return {"result": completion.choices[0].message.content}

def build_prompt(problem, axioms):
    axiom_list = "\n".join([f"{i+1}. {a}" for i, a in enumerate(axioms)])
    return f"""You are ProofGPT. You are restricted to the axioms below:

{axiom_list}

---

Problem:
{problem}

---

Only derive using the axioms. If impossible, reply:
"Undecidable with given axioms.""
"