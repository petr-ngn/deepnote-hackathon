from dotenv import load_dotenv
from src.ui import App
from src.utils import _load_configs

if __name__ == "__main__":

    load_dotenv(override = True)

    config = _load_configs('config')

    app = App(config)

    app.run()
    