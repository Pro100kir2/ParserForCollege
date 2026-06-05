import os
import tempfile
import shutil
import subprocess
from src.readers.docx_reader import DocxReader
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DocReader(DocxReader):
    def supports_format(self, file_path: str) -> bool:
        return file_path.lower().endswith('.doc') and not file_path.lower().endswith('.docx')

    def read(self, file_path: str):
        from src.domain.models import Document
        document = Document(file_path=file_path, file_name=os.path.basename(file_path))
        
        try:
            # Try LibreOffice first (supports legacy .doc format)
            temp_dir = tempfile.mkdtemp()
            abs_file_path = os.path.abspath(file_path)
            temp_docx_path = os.path.join(temp_dir, "converted.docx")
            
            try:
                logger.info(f"Attempting LibreOffice conversion for: {abs_file_path}")
                # Use LibreOffice to convert .doc to .docx
                result = subprocess.run(
                    ['soffice', '--headless', '--convert-to', 'docx', '--outdir', temp_dir, abs_file_path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                logger.debug(f"LibreOffice return code: {result.returncode}")
                logger.debug(f"LibreOffice stdout: {result.stdout}")
                logger.debug(f"LibreOffice stderr: {result.stderr}")
                
                # LibreOffice creates file with original name + .docx
                converted_filename = os.path.basename(abs_file_path) + '.docx'
                actual_converted_path = os.path.join(temp_dir, converted_filename)
                
                if os.path.exists(actual_converted_path):
                    # Use parent class to read the converted DOCX
                    converted_doc = super(DocxReader, self).read(actual_converted_path)
                    document.raw_text = converted_doc.raw_text
                    document.parse_errors = converted_doc.parse_errors
                    logger.info(f"Successfully converted and read DOC file using LibreOffice: {file_path}")
                elif os.path.exists(temp_docx_path):
                    # Fallback to expected filename
                    converted_doc = super(DocxReader, self).read(temp_docx_path)
                    document.raw_text = converted_doc.raw_text
                    document.parse_errors = converted_doc.parse_errors
                    logger.info(f"Successfully converted and read DOC file using LibreOffice (fallback): {file_path}")
                else:
                    logger.warning(f"LibreOffice conversion did not create expected output file. Available files: {os.listdir(temp_dir)}")
                    # Fallback to pypandoc if LibreOffice fails
                    self._try_pypandoc_conversion(file_path, temp_dir, document)
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"LibreOffice conversion timed out for {file_path}, trying pypandoc")
                self._try_pypandoc_conversion(file_path, temp_dir, document)
            except FileNotFoundError:
                logger.warning(f"LibreOffice not found, trying pypandoc for {file_path}")
                self._try_pypandoc_conversion(file_path, temp_dir, document)
            except Exception as e:
                logger.warning(f"LibreOffice conversion failed for {file_path}: {str(e)}, trying pypandoc")
                self._try_pypandoc_conversion(file_path, temp_dir, document)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            error_msg = f"Failed to convert DOC file {file_path}: {str(e)}"
            logger.error(error_msg)
            document.parse_errors.append(error_msg)
        
        return document
    
    def _try_pypandoc_conversion(self, file_path: str, temp_dir: str, document):
        """Try to convert using pypandoc as fallback"""
        try:
            import pypandoc
            temp_docx_path = os.path.join(temp_dir, "converted_pandoc.docx")
            
            pypandoc.convert_file(
                file_path,
                'docx',
                outputfile=temp_docx_path
            )
            
            if os.path.exists(temp_docx_path):
                converted_doc = super(DocxReader, self).read(temp_docx_path)
                document.raw_text = converted_doc.raw_text
                document.parse_errors = converted_doc.parse_errors
                logger.info(f"Successfully converted and read DOC file using pypandoc: {file_path}")
            else:
                error_msg = f"pypandoc conversion failed for {file_path}: output file not created"
                logger.error(error_msg)
                document.parse_errors.append(error_msg)
                
        except ImportError:
            error_msg = f"pypandoc not installed. Cannot convert DOC file {file_path}"
            logger.error(error_msg)
            document.parse_errors.append(error_msg)
        except Exception as e:
            error_msg = f"pypandoc conversion failed for {file_path}: {str(e)}"
            logger.error(error_msg)
            document.parse_errors.append(error_msg)
