"""OpenTelemetry tracing configuration."""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor


def setup_tracing(
    service_name: str = "rag-backend",
    otlp_endpoint: str | None = None,
    enabled: bool = True
) -> None:
    """
    Configure OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service for traces
        otlp_endpoint: OTLP collector endpoint (e.g., "http://otel-collector:4317")
        enabled: Whether to enable tracing
    """
    if not enabled:
        return
    
    # Get endpoint from env or parameter
    endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    
    # Create resource with service name
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })
    
    # Create tracer provider
    provider = TracerProvider(resource=resource)
    
    # Add OTLP exporter if endpoint is configured
    if endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)


def instrument_app(app) -> None:
    """
    Instrument FastAPI app and related libraries.
    
    Args:
        app: FastAPI application instance
    """
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument HTTPX (used for OpenRouter API calls)
    HTTPXClientInstrumentor().instrument()


def instrument_database(engine) -> None:
    """
    Instrument SQLAlchemy engine for tracing.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance for manual span creation."""
    return trace.get_tracer(name)
