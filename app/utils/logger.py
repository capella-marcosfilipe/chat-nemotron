import logging
import sys
from pathlib import Path
from typing import Optional


class Logger:
    """Singleton logger for the entire application."""
    
    _instance: Optional["Logger"] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if Logger._initialized:
            return
        
        self.logger = logging.getLogger("nemotron_service")
        self.logger.setLevel(logging.INFO)
        
        # Evitar duplicação de handlers
        if not self.logger.handlers:
            self._setup_handlers()
        
        Logger._initialized = True
    
    def _setup_handlers(self):
        """Setup console and file handlers."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # File handler
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "nemotron.log")
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the singleton logger instance."""
        return self.logger
    
    # Convenience methods
    def info(self, message: str, **kwargs):
        self.logger.info(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        self.logger.exception(message, **kwargs)


# Global singleton instance
logger = Logger()
