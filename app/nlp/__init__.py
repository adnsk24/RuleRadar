# RuleRadar AI - NLP Package Init
from app.nlp.ingestion import DocumentIngestionPipeline, IngestionError
from app.nlp.segmentation import ClauseSegmenter
from app.nlp.embeddings import embedding_service
from app.nlp.classifier import ClauseClassifier
from app.nlp.risk_engine import RiskEngine
from app.nlp.importance_engine import ImportanceEngine
from app.nlp.extractor import InformationExtractor
from app.nlp.comparison import DocumentComparator
from app.nlp.qa_engine import DocumentQAEngine

__all__ = [
    "DocumentIngestionPipeline",
    "IngestionError",
    "ClauseSegmenter",
    "embedding_service",
    "ClauseClassifier",
    "RiskEngine",
    "ImportanceEngine",
    "InformationExtractor",
    "DocumentComparator",
    "DocumentQAEngine"
]
