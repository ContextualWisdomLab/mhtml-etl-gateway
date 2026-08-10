"""MHTML ETL Gateway — parse SAP ALV / Excel Web Archive MHTML into PostgreSQL."""

from mhtml_etl_gateway.pipeline import convert_mhtml_to_postgres, extract_table

__version__ = "0.1.0"
__all__ = ["convert_mhtml_to_postgres", "extract_table", "__version__"]
