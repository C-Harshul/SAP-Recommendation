"""CloudWatch metrics emission (no-op in dev without AWS)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mypy_boto3_cloudwatch import CloudWatchClient

logger = logging.getLogger(__name__)


class MetricsEmitter:
    """Emit records_ingested, errors, dlq_count per source_id."""

    def __init__(
        self,
        cloudwatch_client: CloudWatchClient | None = None,
        namespace: str = "EG/MarketTrends/Ingestion",
        enabled: bool = True,
    ) -> None:
        self._cw = cloudwatch_client
        self._namespace = namespace
        self._enabled = enabled and cloudwatch_client is not None

    def emit_run_metrics(
        self,
        source_id: str,
        records_ingested: int,
        errors: int,
        dlq_count: int,
    ) -> None:
        if not self._enabled or self._cw is None:
            logger.debug(
                "metrics",
                extra={
                    "source_id": source_id,
                    "records_ingested": records_ingested,
                    "errors": errors,
                    "dlq_count": dlq_count,
                },
            )
            return
        from datetime import UTC, datetime

        ts = datetime.now(UTC)
        dims = [{"Name": "source_id", "Value": source_id}]
        self._cw.put_metric_data(
            Namespace=self._namespace,
            MetricData=[
                {
                    "MetricName": "records_ingested",
                    "Dimensions": dims,
                    "Value": float(records_ingested),
                    "Timestamp": ts,
                },
                {
                    "MetricName": "errors",
                    "Dimensions": dims,
                    "Value": float(errors),
                    "Timestamp": ts,
                },
                {
                    "MetricName": "dlq_count",
                    "Dimensions": dims,
                    "Value": float(dlq_count),
                    "Timestamp": ts,
                },
            ],
        )
