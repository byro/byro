"""Registry of bank transaction importers provided by plugins."""

import logging

from byro.bookkeeping.signals import bank_transaction_importers

from .api import MAX_IDENTIFIER_LENGTH, UnknownImporter

logger = logging.getLogger(__name__)


def _is_valid_importer(importer):
    identifier = getattr(importer, "identifier", None)
    return (
        isinstance(identifier, str)
        and 0 < len(identifier) <= MAX_IDENTIFIER_LENGTH
        and getattr(importer, "label", None)
        and callable(getattr(importer, "parse", None))
    )


def get_bank_transaction_importers():
    """Return all registered importers as a dict keyed by identifier.

    Receivers of ``bank_transaction_importers`` may return a single importer
    or an iterable of importers. Invalid importers and duplicate identifiers
    are logged and skipped, so that a broken plugin does not take down the
    import page.
    """
    importers = {}
    for receiver, response in bank_transaction_importers.send_robust(sender=None):
        if isinstance(response, Exception):
            logger.warning(
                "Bank transaction importer registration failed: receiver=%s.%s",
                receiver.__module__,
                getattr(receiver, "__qualname__", receiver.__class__.__name__),
                exc_info=response,
            )
            continue
        if response is None:
            continue
        if _is_valid_importer(response) or not hasattr(response, "__iter__"):
            response = [response]
        for importer in response:
            if not _is_valid_importer(importer):
                logger.warning(
                    "Ignoring invalid bank transaction importer %r from %s",
                    importer,
                    receiver.__module__,
                )
                continue
            if importer.identifier in importers:
                logger.warning(
                    "Ignoring duplicate bank transaction importer identifier %r from %s",
                    importer.identifier,
                    receiver.__module__,
                )
                continue
            importers[importer.identifier] = importer
    return dict(sorted(importers.items(), key=lambda item: str(item[1].label)))


def get_bank_transaction_importer(identifier):
    """Resolve an importer by its stable identifier.

    Raises :class:`~byro.bookkeeping.bank_import.api.UnknownImporter` if no
    importer with that identifier is registered.
    """
    try:
        return get_bank_transaction_importers()[identifier]
    except KeyError:
        raise UnknownImporter(identifier) from None
