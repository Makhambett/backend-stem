import os
import base64
import httpx
from fastapi import APIRouter, HTTPException, Request
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN")
HF_MODEL_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"


@router.post("/")
async def visualize_interior(request: Request):
    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="HF_TOKEN не настроен в .env")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидный JSON")

    products_list = body.get("products", [])

    if not products_list:
        raise HTTPException(status_code=422, detail="Выберите хотя бы один товар")

    items_text = ", ".join(products_list)
    prompt = (
        f"Modern educational classroom interior design with {items_text}. "
        f"Photorealistic, bright natural lighting, clean walls, "
        f"professional interior design, high quality, 4K."
    )

    print(f"🎨 Промпт: {prompt}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                HF_MODEL_URL,
                headers={
                    "Authorization": f"Bearer {HF_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": prompt,
                },
            )

            if response.status_code == 200:
                result_b64 = base64.b64encode(response.content).decode("utf-8")
                return {
                    "success": True,
                    "image": f"data:image/jpeg;base64,{result_b64}",
                    "prompt": prompt,
                }
            elif response.status_code == 503:
                return {
                    "success": False,
                    "error": "Модель загружается, подождите 20 секунд и попробуйте снова",
                }
            else:
                print(f"❌ HF error {response.status_code}: {response.text}")
                return {"success": False, "error": "Ошибка генерации изображения"}

    except httpx.TimeoutException:
        return {"success": False, "error": "Превышено время ожидания. Попробуйте снова"}
    except Exception as e:
        print(f"❌ Visualize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))