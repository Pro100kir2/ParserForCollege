import argparse
import sys
import os
from src.services.parsing_service import ParsingService
from src.utils.logger import get_logger
from src.utils.tracing import get_tracer
from src.utils.checkpoint import CheckpointManager

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="RPD Document Parser - Extract literature and resources from curriculum documents"
    )
    
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to directory containing RPD documents (.docx, .doc)"
    )
    
    parser.add_argument(
        "--output", "-o",
        help="Output directory for Excel files (default: ./output)"
    )
    
    parser.add_argument(
        "--single-workbook", "-s",
        action="store_true",
        help="Export to single workbook with multiple sheets (default: separate files)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of async workers (default: 4)"
    )
    
    parser.add_argument(
        "--chunk-size", "-c",
        type=int,
        default=1000,
        help="Number of documents per worker chunk (default: 1000)"
    )
    
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint (skip already processed files)"
    )
    
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental mode: process only new or modified files"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(10)  # DEBUG level
    
    try:
        tracer = get_tracer()
        run_id = tracer.start_run()
        
        logger.info("=" * 60)
        logger.info("RPD Document Parser - CLI Mode")
        logger.info(f"Run ID: {run_id}")
        logger.info("=" * 60)
        
        # Validate input path
        if not os.path.exists(args.input):
            logger.error(f"Input path does not exist: {args.input}")
            sys.exit(1)
        
        if not os.path.isdir(args.input):
            logger.error(f"Input path is not a directory: {args.input}")
            sys.exit(1)
        
        # Set output path
        output_path = args.output or "./output"
        
        # Process documents
        service = ParsingService()
        # Override settings with CLI args if provided
        if args.workers:
            service.settings.max_workers = args.workers
        if args.chunk_size:
            service.settings.worker_capacity = args.chunk_size
        
        # Handle resume mode
        if args.resume:
            checkpoint_manager = CheckpointManager()
            processed_files = checkpoint_manager.load_checkpoint(args.input)
            service.set_processed_files(processed_files)
            logger.info(f"Resume mode: skipping {len(processed_files)} already processed files")
        
        # Handle incremental mode
        if args.incremental:
            checkpoint_manager = CheckpointManager()
            processed_files = checkpoint_manager.load_checkpoint(args.input)
            service.set_processed_files(processed_files)
            service.set_incremental_mode(True)
            logger.info(f"Incremental mode: processing only new or modified files")
        
        result = service.process_directory(args.input, output_path)
        
        # Print summary
        print("\n" + "=" * 60)
        print("PROCESSING SUMMARY")
        print("=" * 60)
        print(f"Processed files: {result.processed_files}")
        print(f"Failed files: {result.failed_files}")
        
        if result.failed_file_list:
            print("\nFailed files:")
            for filename in result.failed_file_list:
                print(f"  - {filename}")
        
        print(f"\nExtracted entries:")
        print(f"  Main Literature: {len(result.main_literature)}")
        print(f"  Additional Literature: {len(result.additional_literature)}")
        print(f"  Material Resources: {len(result.material_resources)}")
        
        if result.low_confidence_files:
            print(f"\nLow confidence files (manual review recommended):")
            for filename in result.low_confidence_files:
                print(f"  - {filename}")
        
        # Print metrics
        metrics = service.metrics.get_current_metrics()
        print(f"\nMetrics:")
        print(f"  Execution time: {metrics['execution_time']:.2f}s")
        print(f"  Error rate: {metrics['error_rate']:.2f}%")
        print(f"  Extractor version: {result.extractor_version}")
        
        print(f"\nOutput directory: {output_path}")
        print("=" * 60)
        
        logger.info("CLI execution completed successfully")
        
    except Exception as e:
        logger.error(f"CLI execution failed: {str(e)}")
        print(f"\nError: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
