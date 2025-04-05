from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
import os, time, requests
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

AXIOM_URLS = {
    "hilbert": "https://raw.githubusercontent.com/Harim923/Axiom-Atlas/main/axioms/hilbert.json",
    "euclid": "https://raw.githubusercontent.com/Harim923/Axiom-Atlas/main/axioms/euclid.json",
    "tarski": "https://raw.githubusercontent.com/Harim923/Axiom-Atlas/main/axioms/tarski.json"
}

def fetch_axioms(axiom_set):
    url = AXIOM_URLS.get(axiom_set)
    if not url:
        return []
    res = requests.get(url)
    data = res.json()
    if "groups" in data:
        axioms = [a["statement"] for g in data["groups"] for a in g["axioms"]]
    else:
        axioms = [a["statement"] for a in data["axioms"]]
    return axioms

@app.post("/api/proof")
async def get_proof(req: Request):
    body = await req.json()
    problem = body.get("problem", "").strip()
    axiomSet = body.get("axiomSet", "").lower()

    axioms = fetch_axioms(axiomSet)
    if not axioms:
        raise HTTPException(status_code=400, detail="Invalid or missing axiom set")

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
\"Undecidable with given axioms.\"
"""
