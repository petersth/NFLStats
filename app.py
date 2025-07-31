# app.py - Clean Architecture NFL Statistics Application

import logging
import sys
from src.presentation.streamlit.streamlit_controller import main

def configure_logging():
    """Configure logging to output to console and show debug information."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Set specific loggers to DEBUG for our modules
    logging.getLogger('src.domain.orchestration').setLevel(logging.INFO)
    logging.getLogger('src.infrastructure.factories').setLevel(logging.INFO)
    logging.getLogger('src.application.use_cases').setLevel(logging.INFO)
    
    print("Logging configured - you should see log messages now")

if __name__ == "__main__":
    configure_logging()
    main()