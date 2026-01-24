import httpx
from config import WEBAPP_URL


async def backend_post(path: str, json: dict):
    async with httpx.AsyncClient() as client:
        return await client.post(f"{WEBAPP_URL}{path}", json=json)


async def backend_get(path: str):
    async with httpx.AsyncClient() as client:
        return await client.get(f"{WEBAPP_URL}{path}")


async def backend_delete(path: str):
    async with httpx.AsyncClient() as client:
        return await client.delete(f"{WEBAPP_URL}{path}")
