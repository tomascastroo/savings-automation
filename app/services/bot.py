from ..utils.logging import logger

async def send_user_notification(user_id: int, text: str) -> None:
    logger.info("notify_user", user_id=user_id, text=text)

async def send_whatsapp(phone: str, text: str) -> None:
    # TODO: integrate WhatsApp Business API
    logger.info("whatsapp_stub", phone=phone, text=text)
