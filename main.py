from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_BASE = "https://your-api-domain.com"
API_HEADERS = {
    "Authorization": "YOUR_API_AUTH_TOKEN",
    "Content-Type": "application/json"
}

class TokenCheckRequest(BaseModel):
    tokens: List[str]

@app.post("/api/check-tokens")
async def check_tokens(payload: TokenCheckRequest):
    if not payload.tokens or len(payload.tokens) > 1000:
        raise HTTPException(status_code=400, detail="يجب إرسال بين 1 و 1000 توكن.")

    async with httpx.AsyncClient() as client:
        create_resp = await client.post(
            f"{API_BASE}/task/create",
            headers=API_HEADERS,
            json={"tool": "check", "tokens": payload.tokens}
        )
        
        if create_resp.status_code != 200:
            raise HTTPException(status_code=create_resp.status_code, detail="فشل إنشاء مهمة الفحص.")
            
        job_data = create_resp.json()
        job_id = job_data.get("job_id")

        after = 0
        all_results = []
        
        while True:
            poll_resp = await client.get(
                f"{API_BASE}/task/items",
                headers=API_HEADERS,
                params={"job_id": job_id, "after": after}
            )
            
            if poll_resp.status_code != 200:
                raise HTTPException(status_code=poll_resp.status_code, detail="خطأ أثناء جلب النتائج.")
                
            poll_data = poll_resp.json()
            all_results.extend(poll_data.get("results", []))
            after = poll_data.get("last_id", after)
            
            if poll_data.get("status") != "running":
                break
                
            await asyncio.sleep(1)

        return {
            "status": "success",
            "job_id": job_id,
            "total": len(all_results),
            "results": all_results
        }
