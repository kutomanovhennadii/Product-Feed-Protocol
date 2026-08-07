"""Publisher assembly errors."""


class PublisherBuildError(ValueError):
    """Raised when publisher cannot be assembled from the given configuration."""


__all__ = ["PublisherBuildError"]
