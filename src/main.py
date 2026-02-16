from wearpark.config import Settings
from wearpark.streamer import Streamer

# The main function initializes the Streamer with the configuration settings and starts the streaming process.
def main():
    Streamer(Settings()).run()

# This block checks if the script is being run directly (as the main module) and calls the main function to start the application.
if __name__ == "__main__":
    main()
