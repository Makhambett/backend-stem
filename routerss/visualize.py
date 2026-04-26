import os
import base64
import httpx
from fastapi import APIRouter, HTTPException, Request
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

HF_TOKEN = os.getenv("HF_TOKEN")

# Модель img2img на Hugging Face (бесплатно)
HF_MODEL_URL = "https://api-inference.huggingface.co/models/lllyasviel/sd-controlnet-canny"


@router.post("/")
async def visualize_interior(request: Request):
    if not HF_TOKEN:
        raise HTTPException(status_code=500, detail="HF_TOKEN не настроен в .env")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Невалидный JSON")

    image_base64 = body.get("image")
    products_list = body.get("products", [])

    if not image_base64:
        raise HTTPException(status_code=422, detail="Поле 'image' обязательно")

    if not products_list:
        raise HTTPException(status_code=422, detail="Выберите хотя бы один товар")

    items_text = ", ".join(products_list)
    prompt = (
        f"Modern educational interior with {items_text}. "
        f"Photorealistic, bright, clean, high quality, 4K, interior design."
    )
    negative_prompt = "blurry, low quality, cartoon, ugly, deformed, dark, dirty"

    print(f"🎨 Визуализация запрос: {prompt}")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                HF_MODEL_URL,
                headers={
                    "Authorization": f"Bearer {HF_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": image_base64,
                    "parameters": {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "num_inference_steps": 20,
                        "guidance_scale": 7.5,
                    },
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
        return {"success": False, "error": "Превышено время ожидания (60 сек). Попробуйте снова"}
    except Exception as e:
        print(f"❌ Visualize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))