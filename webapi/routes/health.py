from fastapi import APIRouter


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "platform": "hermes-agent", "service": "webapi"}

@router.get("/v1/chat/completions")
async def probe_chat_completions() -> dict:
    from fastapi import HTTPException
    raise HTTPException(status_code=405, detail="Method Not Allowed")
