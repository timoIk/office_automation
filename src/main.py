"""Main entry point for the Office Automation Bot."""

from src.bot.app import create_bot_app
from src.common.logging import get_logger, setup_logging


def main() -> None:
    setup_logging()
    logger = get_logger(__name__)
    logger.info("starting_bot")

    app = create_bot_app()
    logger.info("bot_configured", mode="polling")
    app.run_polling()


if __name__ == "__main__":
    main()
