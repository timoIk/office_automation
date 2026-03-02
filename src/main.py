"""Main entry point for the Office Automation Bot."""

import asyncio
import signal

from src.bot.app import create_bot_app
from src.common.config import get_settings
from src.common.logging import get_logger, setup_logging


async def _async_main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    settings = get_settings()

    app = create_bot_app()

    # Manual lifecycle instead of blocking run_polling()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    logger.info("bot_started", mode="polling")

    # Start RPA processor alongside the bot
    processor_task = None
    if settings.rpa_enabled:
        from src.rpa.processor import run_processor

        async def _notify(chat_id: int, text: str) -> None:
            await app.bot.send_message(chat_id=chat_id, text=text)

        processor_task = asyncio.create_task(run_processor(_notify))
        logger.info("rpa_processor_launched")
    else:
        logger.info("rpa_disabled_skipping_processor")

    # Wait for shutdown signal
    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("shutdown_signal_received")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler for SIGTERM
            pass

    # On Windows, handle KeyboardInterrupt instead
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("keyboard_interrupt")

    # Graceful shutdown
    logger.info("shutting_down")

    if processor_task and not processor_task.done():
        processor_task.cancel()
        try:
            await processor_task
        except asyncio.CancelledError:
            pass

    await app.updater.stop()
    await app.stop()
    await app.shutdown()

    logger.info("shutdown_complete")


def main() -> None:
    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
