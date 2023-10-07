import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

try:
    from core.bot import FortniteBot
except ModuleNotFoundError as error:
    logging.fatal(f'Missing required dependencies; see requirements.txt - {error}')
    raise SystemExit()


if __name__ == '__main__':

    bot = FortniteBot()
    bot.run_bot()
