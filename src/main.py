from .config import Settings
from .streamer import Streamer

def main():
    Streamer(Settings()).run()

if __name__ == "__main__":
    main()
