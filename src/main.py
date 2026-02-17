from wearpark.config import Settings
from wearpark.streamer import Streamer
from wearpark.errors import WearParkError

# The main function initializes the Streamer with the configuration settings and starts the streaming process.
def main():
    try:
        Streamer(Settings()).run()
    except WearParkError as e:
        print(f"ERROR {e.code}: {e}")
        raise SystemExit(1) from e

# This block checks if the script is being run directly (as the main module) and calls the main function to start the application.
if __name__ == "__main__":
    main()
