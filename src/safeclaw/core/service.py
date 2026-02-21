import logging
from safeclaw.core.engine import SafeClaw

logger = logging.getLogger(__name__)

class MCPService:
    """
    Wrapper around SafeClaw engine to be used by MCP server.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPService, cls).__new__(cls)
            cls._instance.engine = SafeClaw()
        return cls._instance

    async def initialize(self):
        """Initialize the engine components."""
        logger.info("Initializing SafeClaw engine for MCP...")
        self.engine.load_config()
        await self.engine.memory.initialize()
        # We don't start the scheduler or channels as we are driving it via MCP
        logger.info("SafeClaw engine initialized.")

    async def shutdown(self):
        """Shutdown the engine components."""
        logger.info("Shutting down SafeClaw engine...")
        await self.engine.memory.close()
        logger.info("SafeClaw engine shutdown.")

    def get_engine(self) -> SafeClaw:
        return self.engine

service = MCPService()
