import os
import asyncio
from typing import List
from src.domain.models import Document, ParseResult, SectionType, ExportConfig
from src.readers.reader_factory import ReaderFactory
from src.extractors.section_extractor import SectionExtractor
from src.processors.normalizer import TextNormalizer
from src.processors.deduplicator import Deduplicator
from src.exporters.excel_exporter import ExcelExporter
from src.exporters.word_exporter import WordExporter
from src.config.settings import get_settings
from src.utils.logger import get_logger
from src.utils.metrics import MetricsCollector
from src.services.async_worker import process_files_async

logger = get_logger(__name__)


class ParsingService:
    def __init__(self):
        self.reader_factory = ReaderFactory()
        self.section_extractor = SectionExtractor()
        self.normalizer = TextNormalizer()
        self.deduplicator = Deduplicator()
        self.excel_exporter = ExcelExporter()
        self.word_exporter = WordExporter()
        self.settings = get_settings()
        self.metrics = MetricsCollector()
        self.processed_files_set: set = set()
        self.incremental_mode: bool = False
    
    def process_directory(self, input_path: str, output_path: str = None) -> ParseResult:
        self.metrics.start_processing()
        
        logger.info(f"Starting processing of directory: {input_path}")
        
        if not os.path.exists(input_path):
            raise ValueError(f"Input path does not exist: {input_path}")
        
        if not os.path.isdir(input_path):
            raise ValueError(f"Input path is not a directory: {input_path}")
        
        documents = self._read_documents(input_path)
        self.metrics.current_metrics.total_files = len(documents)
        
        result = self._process_documents(documents)
        
        if output_path:
            self._export_result(result, output_path)
        else:
            self._export_result(result, self.settings.default_output_dir)
        
        self.metrics.finish_processing()
        
        # Check for alerts
        if self.metrics.check_alerts(self.settings.alert_error_threshold, self.settings.alert_error_window_minutes):
            logger.warning(f"Error threshold exceeded: {result.failed_files} failures")
        
        # Set extractor version
        result.extractor_version = self.settings.extractor_version
        
        # Save checkpoint if not in incremental mode
        if not self.incremental_mode:
            from src.utils.checkpoint import CheckpointManager
            checkpoint_manager = CheckpointManager()
            processed_files = [doc.file_name for doc in documents if doc.file_name not in result.failed_file_list]
            checkpoint_manager.save_checkpoint(input_path, processed_files)
        
        logger.info(f"Processing completed. Processed: {result.processed_files}, Failed: {result.failed_files}, Low confidence: {len(result.low_confidence_files)}")
        return result
    
    def set_processed_files(self, processed_files: List[str]):
        """Set set of already processed files for resume mode"""
        self.processed_files_set = set(processed_files)
    
    def set_incremental_mode(self, enabled: bool):
        """Enable or disable incremental processing mode"""
        self.incremental_mode = enabled
    
    async def process_directory_async(self, input_path: str, output_path: str = None) -> ParseResult:
        self.metrics.start_processing()
        
        logger.info(f"Starting async processing of directory: {input_path}")
        
        if not os.path.exists(input_path):
            raise ValueError(f"Input path does not exist: {input_path}")
        
        if not os.path.isdir(input_path):
            raise ValueError(f"Input path is not a directory: {input_path}")
        
        documents = self._read_documents(input_path)
        self.metrics.current_metrics.total_files = len(documents)
        
        result = await self._process_documents_async(documents)
        
        if output_path:
            self._export_result(result, output_path)
        else:
            self._export_result(result, self.settings.default_output_dir)
        
        self.metrics.finish_processing()
        
        if self.metrics.check_alerts(self.settings.alert_error_threshold, self.settings.alert_error_window_minutes):
            logger.warning(f"Error threshold exceeded: {result.failed_files} failures")
        
        logger.info(f"Async processing completed. Processed: {result.processed_files}, Failed: {result.failed_files}")
        return result

    def _read_documents(self, directory: str) -> List[Document]:
        documents = []
        supported_extensions = ['.docx']  # .doc полностью убрали

        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)

            if not os.path.isfile(file_path):
                continue

            # Пропускаем .doc файлы
            if filename.lower().endswith('.doc'):
                logger.info(f"Пропущен файл неподдерживаемого формата (.doc): {filename}")
                continue

            # Пропускаем временные файлы Word
            if (filename.startswith('~$') or
                    filename.startswith('~$_') or
                    filename.startswith('~')):
                logger.info(f"Skipping temporary file: {filename}")
                continue

            # Проверяем поддерживаемые расширения
            if not any(filename.lower().endswith(ext) for ext in supported_extensions):
                logger.warning(f"Skipping unsupported file: {filename}")
                continue

            # Skip if already processed (resume mode)
            if filename in self.processed_files_set:
                logger.info(f"Skipping already processed: {filename}")
                continue

            reader = self.reader_factory.get_reader(file_path)
            if reader:
                try:
                    document = reader.read(file_path)
                    documents.append(document)
                except Exception as e:
                    logger.error(f"Failed to read {filename}: {str(e)}", exc_info=True)
                    documents.append(Document(
                        file_path=file_path,
                        file_name=filename,
                        parse_errors=[str(e)]
                    ))
            else:
                logger.warning(f"No reader available for: {filename}")

        logger.info(f"Read {len(documents)} documents")
        return documents
    
    def _process_documents(self, documents: List[Document]) -> ParseResult:
        result = ParseResult()
        
        for document in documents:
            try:
                # Skip documents with parse errors
                if document.parse_errors:
                    logger.warning(f"Skipping document with parse errors: {document.file_name}")
                    result.failed_files += 1
                    result.failed_file_list.append(document.file_name)
                    self.metrics.record_failure(document.file_name, "; ".join(document.parse_errors))
                    continue
                
                # Ensure raw_text attribute exists
                if not hasattr(document, 'raw_text'):
                    document.raw_text = ""
                
                # Extract sections
                document = self.section_extractor.extract_sections(document)
                
                # Collect entries
                for section_type, section_content in document.sections.items():
                    entries = section_content.entries
                    normalized_entries = self.normalizer.normalize_list(entries)
                    
                    if section_type == SectionType.MAIN_LITERATURE:
                        result.main_literature.extend(normalized_entries)
                    elif section_type == SectionType.ADDITIONAL_LITERATURE:
                        result.additional_literature.extend(normalized_entries)
                    elif section_type == SectionType.MATERIAL_RESOURCES:
                        result.material_resources.extend(normalized_entries)
                
                result.processed_files += 1
                self.metrics.record_success()
                
                # Check for low confidence sections
                for section_type, section_content in document.sections.items():
                    if section_content.confidence_score < self.settings.confidence_threshold:
                        if document.file_name not in result.low_confidence_files:
                            result.low_confidence_files.append(document.file_name)
                        logger.warning(f"Low confidence {section_type.value} in {document.file_name}: {section_content.confidence_score:.2f}")
                
                logger.info(f"Successfully processed: {document.file_name}")
                
            except Exception as e:
                result.failed_files += 1
                result.failed_file_list.append(document.file_name)
                self.metrics.record_failure(document.file_name, str(e))
                logger.error(f"Failed to process {document.file_name}: {str(e)}", exc_info=True)
        
        # Deduplicate
        try:
            result.main_literature = self.deduplicator.deduplicate(result.main_literature)
            result.additional_literature = self.deduplicator.deduplicate(result.additional_literature)
            result.material_resources = self.deduplicator.deduplicate(result.material_resources)
        except Exception as e:
            logger.error(f"Error during deduplication: {str(e)}", exc_info=True)
        
        # Optional: Apply fuzzy deduplication
        if self.settings.fuzzy_deduplication_threshold > 0:
            try:
                logger.info(f"Applying fuzzy deduplication with threshold {self.settings.fuzzy_deduplication_threshold}")
                result.main_literature = self.deduplicator.fuzzy_deduplicate(result.main_literature, self.settings.fuzzy_deduplication_threshold)
                result.additional_literature = self.deduplicator.fuzzy_deduplicate(result.additional_literature, self.settings.fuzzy_deduplication_threshold)
                result.material_resources = self.deduplicator.fuzzy_deduplicate(result.material_resources, self.settings.fuzzy_deduplication_threshold)
            except Exception as e:
                logger.error(f"Error during fuzzy deduplication: {str(e)}", exc_info=True)
        
        logger.info(f"Deduplication complete. Main: {len(result.main_literature)}, "
                   f"Additional: {len(result.additional_literature)}, "
                   f"Material: {len(result.material_resources)}")
        
        return result
    
    async def _process_documents_async(self, documents: List[Document]) -> ParseResult:
        result = ParseResult()
        
        async def process_document_chunk(doc_chunk: List[Document]) -> dict:
            chunk_result = {
                'main_literature': [],
                'additional_literature': [],
                'material_resources': [],
                'processed': 0,
                'failed': 0,
                'failed_list': []
            }
            
            for document in doc_chunk:
                try:
                    # Skip documents with parse errors
                    if document.parse_errors:
                        logger.warning(f"Skipping document with parse errors: {document.file_name}")
                        chunk_result['failed'] += 1
                        chunk_result['failed_list'].append(document.file_name)
                        self.metrics.record_failure(document.file_name, "; ".join(document.parse_errors))
                        continue
                    
                    # Ensure raw_text attribute exists
                    if not hasattr(document, 'raw_text'):
                        document.raw_text = ""
                    
                    document = self.section_extractor.extract_sections(document)
                    
                    for section_type, section_content in document.sections.items():
                        entries = section_content.entries
                        normalized_entries = self.normalizer.normalize_list(entries)
                        
                        if section_type == SectionType.MAIN_LITERATURE:
                            chunk_result['main_literature'].extend(normalized_entries)
                        elif section_type == SectionType.ADDITIONAL_LITERATURE:
                            chunk_result['additional_literature'].extend(normalized_entries)
                        elif section_type == SectionType.MATERIAL_RESOURCES:
                            chunk_result['material_resources'].extend(normalized_entries)
                    
                    chunk_result['processed'] += 1
                    self.metrics.record_success()
                    logger.info(f"Successfully processed: {document.file_name}")
                    
                except Exception as e:
                    chunk_result['failed'] += 1
                    chunk_result['failed_list'].append(document.file_name)
                    self.metrics.record_failure(document.file_name, str(e))
                    logger.error(f"Failed to process {document.file_name}: {str(e)}", exc_info=True)
            
            return chunk_result
        
        # Split documents into chunks based on worker_capacity
        chunk_size = self.settings.worker_capacity
        chunks = [documents[i:i + chunk_size] for i in range(0, len(documents), chunk_size)]
        
        # Process chunks asynchronously
        chunk_results, errors = await process_files_async(
            chunks,
            process_document_chunk,
            max_workers=self.settings.max_workers,
            chunk_size=1  # Each chunk is already sized by worker_capacity
        )
        
        # Aggregate results
        for chunk_result in chunk_results:
            result.main_literature.extend(chunk_result['main_literature'])
            result.additional_literature.extend(chunk_result['additional_literature'])
            result.material_resources.extend(chunk_result['material_resources'])
            result.processed_files += chunk_result['processed']
            result.failed_files += chunk_result['failed']
            result.failed_file_list.extend(chunk_result['failed_list'])
        
        # Deduplicate
        try:
            result.main_literature = self.deduplicator.deduplicate(result.main_literature)
            result.additional_literature = self.deduplicator.deduplicate(result.additional_literature)
            result.material_resources = self.deduplicator.deduplicate(result.material_resources)
        except Exception as e:
            logger.error(f"Error during async deduplication: {str(e)}", exc_info=True)
        
        logger.info(f"Async deduplication complete. Main: {len(result.main_literature)}, "
                   f"Additional: {len(result.additional_literature)}, "
                   f"Material: {len(result.material_resources)}")
        
        return result
    
    def _export_result(self, result: ParseResult, output_dir: str):
        config = ExportConfig(
            single_workbook=self.settings.single_workbook_export,
            output_dir=output_dir
        )
        output_files = self.word_exporter.export(result, config)
        logger.info(f"Exported files: {output_files}")
