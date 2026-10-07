from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
import asyncio
from typing import List
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenCheckRequest(BaseModel):
    tokens: List[str]

@app.get("/")
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Server is running, but index.html is missing."}

async def check_single_token(client: httpx.AsyncClient, token: str):
    # تنظيف التوكن لو كان بصيغة email:pass:token
    clean_token = token.split(":")[-1].strip() if ":" in token else token.strip()
    
    headers = {"Authorization": clean_token}
    
    try:
        # فحص بيانات الحساب الأساسية من ديسكورد
        res = await client.get("https://discord.com/api/v9/users/@me", headers=headers)
        
        if res.status_code == 200:
            user_data = res.json()
            premium_type = user_data.get("premium_type", 0)
            
            # تحديد نوع النيترو
            nitro_status = False
            nitro_type = "لا يوجد"
            if premium_type == 1:
                nitro_status = True
                nitro_type = "Nitro Classic"
            elif premium_type == 2:
                nitro_status = True
                nitro_type = "Nitro Boost"
            elif premium_type == 3:
                nitro_status = True
                nitro_type = "Nitro Basic"

            return {
                "token": clean_token,
                "status": "valid",
                "username": f"{user_data.get('username')}#{user_data.get('discriminator', '0')}",
                "user_id": user_data.get("id"),
                "email": user_data.get("email"),
                "phone": user_data.get("phone"),
                "nitro": nitro_status,
                "nitro_type": nitro_type,
                "verified": user_data.get("verified", False)
            }
        elif res.status_code == 403:
            return {"token": clean_token, "status": "locked", "username": "N/A", "nitro": False}
        else:
            return {"token": clean_token, "status": "invalid", "username": "N/A", "nitro": False}
    except Exception:
        return {"token": clean_token, "status": "error", "username": "N/A", "nitro": False}

@app.post("/api/check-tokens")
async def check_tokens(payload: TokenCheckRequest):
    if not payload.tokens or len(payload.tokens) > 1000:
        raise HTTPException(status_code=400, detail="أدخل من 1 إلى 1000 توكن.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # فحص جميع التوكنات بالتوازي لسرعة الأداء
        tasks = [check_single_token(client, token) for token in payload.tokens]
        results = await asyncio.gather(*tasks)

    return {
        "status": "success",
        "total": len(results),
        "results": results
    }
