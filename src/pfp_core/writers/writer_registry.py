"""Writer registry for schema-selected output writers."""

from types import MappingProxyType
from typing import Callable, Dict, Tuple, cast

from pfp_core.writers.writer_base import Writer
from pfp_core.writers.writer_types import ArtifactMeta, WriterConfig, WriterId

WriterFactory = Callable[[WriterConfig, ArtifactMeta], Writer]


class UnknownWriterError(KeyError):
    """Raised when registry lookup uses an unknown writer_id."""


class WriterRegistry:
    """In-memory registry mapping writer identifiers to writer factories."""

    def __init__(self) -> None:
        """Initialize empty in-memory writer factory registry.

        Returns:
            None.
        """
        self._factories: Dict[WriterId, WriterFactory] = {}

    def register(self, writer_id: WriterId, factory: WriterFactory) -> None:
        """Register a writer factory under a writer identifier.

        Args:
            writer_id: Non-empty writer identifier.
            factory: Factory creating a writer from config and artifact metadata.

        Returns:
            None.

        Raises:
            ValueError: If writer_id is empty or already registered.
        """

        if not writer_id:
            raise ValueError("registry error: writer_id must be non-empty")
        if writer_id in self._factories:
            raise ValueError(
                "registry error: writer_id already registered: writer_id=" + writer_id
            )
        self._factories[writer_id] = factory

    def get_factory(self, writer_id: WriterId) -> WriterFactory:
        """Resolve a writer factory by writer identifier.

        Args:
            writer_id: Writer identifier to resolve.

        Returns:
            Registered writer factory.

        Raises:
            UnknownWriterError: If writer_id is not registered.
        """

        try:
            return self._factories[writer_id]
        except KeyError as exc:
            raise UnknownWriterError(
                "registry error: unknown writer_id=" + writer_id
            ) from exc

    def create(
        self,
        writer_id: WriterId,
        writer_config: WriterConfig,
        artifact_meta: ArtifactMeta,
    ) -> Writer:
        """Create a writer instance using the registered factory.

        Args:
            writer_id: Writer identifier to instantiate.
            writer_config: Writer configuration mapping.
            artifact_meta: Artifact metadata mapping.

        Returns:
            Writer instance created by the registered factory.

        Raises:
            UnknownWriterError: If writer_id is not registered.

        Notes:
            Inputs are copied and wrapped into MappingProxyType to enforce
            immutability.
        """

        factory = self.get_factory(writer_id)
        immutable_config = cast(WriterConfig, MappingProxyType(dict(writer_config)))
        immutable_artifact_meta = cast(
            ArtifactMeta,
            MappingProxyType(dict(artifact_meta)),
        )
        return factory(
            immutable_config,
            immutable_artifact_meta,
        )

    def list_ids(self) -> Tuple[WriterId, ...]:
        """Return deterministically sorted writer identifiers.

        Returns:
            Sorted tuple of registered writer identifiers.
        """

        return tuple(sorted(self._factories.keys()))
