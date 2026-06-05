import json
import os
from typing import List, Set
from datetime import datetime
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CheckpointManager:
    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_checkpoint_file(self, input_path: str) -> Path:
        """Generate checkpoint file path based on input directory hash"""
        import hashlib
        dir_hash = hashlib.md5(input_path.encode()).hexdigest()[:8]
        return self.checkpoint_dir / f"checkpoint_{dir_hash}.json"
    
    def save_checkpoint(self, input_path: str, processed_files: List[str]):
        """Save checkpoint with processed files list"""
        checkpoint_file = self._get_checkpoint_file(input_path)
        checkpoint_data = {
            "input_path": input_path,
            "processed_files": processed_files,
            "timestamp": datetime.now().isoformat(),
            "count": len(processed_files)
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Checkpoint saved: {len(processed_files)} files processed")
    
    def load_checkpoint(self, input_path: str) -> List[str]:
        """Load checkpoint and return list of processed files"""
        checkpoint_file = self._get_checkpoint_file(input_path)
        
        if not checkpoint_file.exists():
            return []
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            processed_files = data.get("processed_files", [])
            logger.info(f"Checkpoint loaded: {len(processed_files)} files previously processed")
            return processed_files
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {str(e)}")
            return []
    
    def clear_checkpoint(self, input_path: str):
        """Clear checkpoint for given input path"""
        checkpoint_file = self._get_checkpoint_file(input_path)
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info(f"Checkpoint cleared for: {input_path}")
    
    def get_processed_set(self, input_path: str) -> Set[str]:
        """Get set of processed file names"""
        return set(self.load_checkpoint(input_path))
