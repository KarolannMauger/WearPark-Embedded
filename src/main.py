from wearpark.config import Settings
from wearpark.streamer import Streamer

def main():
    Streamer(Settings()).run()

if __name__ == "__main__":
    main()
