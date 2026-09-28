import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.services.adapters.base import ExternalSystemAdapter
from app.services.adapters.exceptions import ExternalSystemNotConfiguredError
from app.services.adapters.sap_adapter import SAPAdapter, MockSAPAdapter
from app.services.adapters.coalnet_adapter import CoalNetAdapter, MockCoalNetAdapter
from app.services.adapters.dms_adapter import DMSAdapter, MockDMSAdapter

logger = logging.getLogger(__name__)


class ExternalSystemManager:
    """
    Registry and lifecycle manager for Enterprise System Integration Adapters.
    Routes queries to SAP, CoalNet, and DMS adapters while enforcing:
    - Fail-closed defense against invoking unconfigured production systems.
    - Uniform canonical data conversion.
    - Credential-safe health monitoring.
    - Seamless switching between production connectors and deterministic mocks.
    """
    def __init__(self, use_mocks: Optional[bool] = None):
        self._adapters: Dict[str, ExternalSystemAdapter] = {}
        mock_mode = (
            use_mocks
            if use_mocks is not None
            else getattr(settings, "EXTERNAL_SYSTEM_MOCK_ENABLED", False)
        )
        self.initialize_default_adapters(use_mocks=mock_mode)

    def initialize_default_adapters(self, use_mocks: bool = False) -> None:
        """
        Initializes core enterprise adapters (SAP, CoalNet, DMS).
        """
        self._adapters.clear()
        if use_mocks:
            self.register_adapter(MockSAPAdapter())
            self.register_adapter(MockCoalNetAdapter())
            self.register_adapter(MockDMSAdapter())
            logger.info("ExternalSystemManager initialized with deterministic MOCK adapters.")
        else:
            self.register_adapter(SAPAdapter())
            self.register_adapter(CoalNetAdapter())
            self.register_adapter(DMSAdapter())
            logger.info("ExternalSystemManager initialized with standard enterprise adapters.")

    def register_adapter(self, adapter: ExternalSystemAdapter) -> None:
        """
        Registers an enterprise adapter.
        """
        if not isinstance(adapter, ExternalSystemAdapter):
            raise TypeError(f"Adapter must be an instance of ExternalSystemAdapter, got {type(adapter)}")
        key = adapter.system_name.lower().strip()
        self._adapters[key] = adapter

    def unregister_adapter(self, system_name: str) -> Optional[ExternalSystemAdapter]:
        key = system_name.lower().strip()
        return self._adapters.pop(key, None)

    def has_adapter(self, system_name: str) -> bool:
        return system_name.lower().strip() in self._adapters

    def get_adapter(
        self,
        system_name: str,
        require_configured: bool = False
    ) -> ExternalSystemAdapter:
        """
        Retrieves adapter by system name.
        Prevents accidental operations on unconfigured systems when require_configured is True.
        """
        key = system_name.lower().strip()
        adapter = self._adapters.get(key)
        if not adapter:
            raise ExternalSystemNotConfiguredError(
                f"No enterprise adapter registered for system '{system_name}'.",
                system_name=system_name
            )

        if require_configured and not adapter.is_configured:
            raise ExternalSystemNotConfiguredError(
                f"External system adapter '{system_name}' is registered but not configured in this environment.",
                system_name=system_name
            )

        return adapter

    def list_adapters(self) -> List[Dict[str, Any]]:
        """
        Lists all registered adapters and their operational posture.
        """
        result = []
        for key, adapter in sorted(self._adapters.items()):
            result.append({
                "system_name": adapter.system_name,
                "system_type": adapter.system_type,
                "is_mock": adapter.is_mock,
                "is_configured": adapter.is_configured
            })
        return result

    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Gathers safe health telemetry across all registered adapters.
        """
        health_report = {}
        for key, adapter in self._adapters.items():
            try:
                health_report[key] = adapter.health()
            except Exception as e:
                health_report[key] = {
                    "system_name": adapter.system_name,
                    "status": "ERROR",
                    "message": f"Health check execution failed: {str(e)}",
                    "is_mock": adapter.is_mock,
                    "configured": False
                }
        return health_report

    def fetch_all_incremental(
        self,
        since: datetime,
        systems: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates cross-system delta ingestion across all configured enterprise sources.
        """
        targets = [s.lower().strip() for s in systems] if systems else list(self._adapters.keys())
        results = {}
        for name in targets:
            adapter = self._adapters.get(name)
            if not adapter or not adapter.is_configured:
                continue
            try:
                results[name] = adapter.fetch_incremental(since)
            except Exception as e:
                logger.warning(f"Incremental sync failed for '{name}': {e}")
                results[name] = {"error": str(e), "status": "FAILED"}

        return {
            "synced_at": datetime.utcnow().isoformat(),
            "since": since.isoformat(),
            "systems": results
        }


_global_manager: Optional[ExternalSystemManager] = None

def get_system_manager(use_mocks: Optional[bool] = None) -> ExternalSystemManager:
    """
    Factory function to retrieve or create the application-wide ExternalSystemManager.
    """
    global _global_manager
    if _global_manager is None or use_mocks is not None:
        _global_manager = ExternalSystemManager(use_mocks=use_mocks)
    return _global_manager
