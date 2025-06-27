"""
Enhanced PDF Reader with Image Detection and Captioning

Combines LlamaIndex PDFReader with fast image detection and OpenAI Vision captioning
similar to CustomPptxReader.py approach.
"""

# TODO WARNING: This implementation is not working as expected.

import io
import os
import tempfile
import logging
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from tenacity import retry, stop_after_attempt

from dotenv import load_dotenv

load_dotenv()

from fsspec import AbstractFileSystem
from openai import AsyncOpenAI
from llama_index.core.readers.base import BaseReader
from llama_index.core.readers.file.base import get_default_fs, is_default_fs
from llama_index.core.schema import Document

# Import agents like in CustomPptxReader
from agents import Agent, Runner

# Import for fast image detection
try:
    import fitz  # PyMuPDF for fast image detection
except ImportError:
    fitz = None

logger = logging.getLogger(__name__)
RETRY_TIMES = 3

def get_default_caption_agent(model_name: str = "gpt-4o"):
    """Create default caption agent - similar to CustomPptxReader approach"""
    return Agent(
        name="PDF Image Caption Agent",
        model=model_name,
        instructions="You are an expert at describing images from PDF documents. Describe images concisely, focusing on key visual elements, text, charts, diagrams, or important document content.",
    )

class EnhancedPDFReader(BaseReader):
    """Enhanced PDF parser with fast image detection and OpenAI Vision captioning."""

    def __init__(
        self, 
        return_full_document: Optional[bool] = False,
        enable_image_captioning: bool = True,
        openai_api_key: Optional[str] = None,
        image_caption_prompt: str = "Describe this image concisely, focusing on key visual elements, text, charts, or diagrams.",
        enable_fast_image_detection: bool = True,
        model_name: str = "gpt-4o"
    ) -> None:
        """
        Initialize Enhanced PDFReader.
        
        Args:
            return_full_document: Whether to return full document or page-by-page
            enable_image_captioning: Whether to caption images using OpenAI Vision Agents
            openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            image_caption_prompt: Prompt for image captioning (used in agent instructions)
            enable_fast_image_detection: Use PyMuPDF for fast image detection
            model_name: OpenAI model for image captioning agent
        """
        self.return_full_document = return_full_document
        self.enable_image_captioning = enable_image_captioning
        self.enable_fast_image_detection = enable_fast_image_detection and fitz is not None
        self.model_name = model_name
        self.image_caption_prompt = image_caption_prompt
        
        # Initialize caption agent like in CustomPptxReader
        if self.enable_image_captioning:
            self.caption_agent = get_default_caption_agent(self.model_name)
            # Also keep OpenAI client for file uploads
            self.openai_client = AsyncOpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        else:
            self.caption_agent = None
            self.openai_client = None
            
        # Setup logger like in CustomPptxReader
        self.logger = logging.getLogger(__name__)
        if self.enable_image_captioning and self.caption_agent:
            self.logger.info(f"EnhancedPDFReader initialized with model: {self.caption_agent.model}")

    async def caption_image_async(self, image_bytes: bytes, image_format: str = "png") -> str:
        """Generate text caption of image using Agents - exactly like CustomPptxReader approach."""
        if not self.caption_agent or not self.openai_client:
            return "Image captioning disabled"
            
        temp_openai_file_id = None
        
        try:
            # Save image temporarily
            with tempfile.NamedTemporaryFile(suffix=f".{image_format}", delete=False) as tmp_file:
                tmp_file.write(image_bytes)
                tmp_file_path = tmp_file.name
            
            try:
                # Upload to OpenAI Files API (same as CustomPptxReader)
                with open(tmp_file_path, 'rb') as f:
                    file_response = await self.openai_client.files.create(
                        file=f,
                        purpose="vision"
                    )
                    temp_openai_file_id = file_response.id
                
                if self.logger:
                    self.logger.debug(f"Uploaded to OpenAI with file_id: {temp_openai_file_id}")
                
                # Use agents Runner like in CustomPptxReader
                result = await asyncio.wait_for(
                    Runner.run(
                        self.caption_agent,
                        [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "input_image",
                                        "file_id": temp_openai_file_id
                                    }
                                ]
                            }
                        ],
                    ),
                    timeout=60.0  # 60 second timeout
                )
                
                result = result.final_output
                if self.logger:
                    self.logger.debug(f"Vision API response: {result}")
                
                return result or "No description provided"
                
            finally:
                # Cleanup temp file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
                    
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.error(f"Timeout processing image")
            return "Error: Image processing timed out after 60 seconds"
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error captioning image: {e}")
            return f"Error captioning image: {str(e)}"
            
        finally:
            # Cleanup: Delete OpenAI file
            if temp_openai_file_id:
                try:
                    await self.openai_client.files.delete(temp_openai_file_id)
                    if self.logger:
                        self.logger.debug(f"Deleted OpenAI file: {temp_openai_file_id}")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Failed to delete OpenAI file {temp_openai_file_id}: {e}")

    def has_images_fast(self, file_path: Path) -> tuple[bool, int, List[Dict[str, Any]]]:
        """
        Fast image detection using PyMuPDF.
        
        Returns:
            (has_images, total_image_count, image_info_by_page)
        """
        if not self.enable_fast_image_detection:
            return False, 0, []
            
        try:
            doc = fitz.Document(str(file_path))
            total_images = 0
            image_info_by_page = []
            
            for page_num in range(doc.page_count):
                page = doc[page_num]
                image_list = page.get_images()
                page_image_count = len(image_list)
                total_images += page_image_count
                
                # Store basic image info for later processing
                page_images = []
                for img_index, img in enumerate(image_list):
                    try:
                        # Get basic image info without extracting the full image data yet
                        xref = img[0]
                        page_images.append({
                            'page_num': page_num,
                            'img_index': img_index,
                            'xref': xref,
                            'img_info': img  # Full image info from PyMuPDF
                        })
                    except Exception as e:
                        self.logger.warning(f"Error getting image info on page {page_num}, image {img_index}: {e}")
                
                image_info_by_page.append(page_images)
            
            page_count = doc.page_count  # Store before closing
            doc.close()
            has_images = total_images > 0
            
            self.logger.info(f"Fast image detection: {total_images} images found across {page_count} pages")
            return has_images, total_images, image_info_by_page
            
        except Exception as e:
            self.logger.error(f"Fast image detection failed: {e}")
            return False, 0, []

    async def extract_and_caption_images(self, file_path: Path, image_info_by_page: List[List[Dict[str, Any]]]) -> Dict[int, List[str]]:
        """
        Extract images and generate captions.
        
        Returns:
            Dict mapping page_num to list of image captions
        """
        captions_by_page = {}
        
        if not self.enable_image_captioning or not image_info_by_page:
            return captions_by_page
            
        doc = None
        try:
            doc = fitz.Document(str(file_path))
            
            for page_num, page_images in enumerate(image_info_by_page):
                if not page_images:
                    continue
                    
                page_captions = []
                
                for img_info in page_images:
                    try:
                        # Extract the actual image data
                        xref = img_info['xref']
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        # Generate caption
                        caption = await self.caption_image_async(image_bytes, image_ext)
                        page_captions.append(f"Image {img_info['img_index'] + 1}: {caption}")
                        
                        self.logger.info(f"Captioned image {img_info['img_index'] + 1} on page {page_num + 1}")
                        
                        # Small delay to avoid rate limiting
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        self.logger.error(f"Error captioning image {img_info['img_index']} on page {page_num}: {e}")
                        page_captions.append(f"Image {img_info['img_index'] + 1}: Error captioning image")
                
                if page_captions:
                    captions_by_page[page_num] = page_captions
            
        except Exception as e:
            self.logger.error(f"Image extraction and captioning failed: {e}")
            
        finally:
            if doc:
                doc.close()
            
        return captions_by_page

    @retry(stop=stop_after_attempt(RETRY_TIMES))
    async def load_data_async(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Parse file with async image captioning."""
        if not isinstance(file, Path):
            file = Path(file)

        # Step 1: Fast image detection
        has_images, total_images, image_info_by_page = self.has_images_fast(file)
        
        self.logger.info(f"Processing PDF: {file.name}")
        self.logger.info(f"Images detected: {total_images}")

        # Step 2: Extract and caption images if found
        captions_by_page = {}
        if has_images and self.enable_image_captioning and total_images > 0:
            self.logger.info("Starting image captioning...")
            captions_by_page = await self.extract_and_caption_images(file, image_info_by_page)
            self.logger.info(f"Captioned images on {len(captions_by_page)} pages")
        elif self.enable_image_captioning and total_images == 0:
            self.logger.info("No images found for captioning")

        # Step 3: Extract text using pypdf (following original LlamaIndex approach)
        try:
            import pypdf
        except ImportError:
            raise ImportError("pypdf is required to read PDF files: `pip install pypdf`")
            
        fs = fs or get_default_fs()
        with fs.open(str(file), "rb") as fp:
            stream = fp if is_default_fs(fs) else io.BytesIO(fp.read())
            pdf = pypdf.PdfReader(stream)
            num_pages = len(pdf.pages)

            docs = []

            # Step 4: Combine text and image captions
            if self.return_full_document:
                # Return whole PDF as single document
                metadata = {"file_name": file.name, "total_images": total_images}
                if extra_info is not None:
                    metadata.update(extra_info)

                # Extract text from all pages
                all_text_parts = []
                for page_num in range(num_pages):
                    page_text = pdf.pages[page_num].extract_text()
                    
                    # Add page header
                    all_text_parts.append(f"\n--- Page {page_num + 1} ---")
                    
                    # Add page text
                    if page_text.strip():
                        all_text_parts.append(page_text)
                    
                    # Add image captions for this page
                    if page_num in captions_by_page:
                        all_text_parts.append("\n[IMAGES ON THIS PAGE]")
                        for caption in captions_by_page[page_num]:
                            all_text_parts.append(f"- {caption}")
                        all_text_parts.append("[END IMAGES]\n")

                full_text = "\n".join(all_text_parts)
                docs.append(Document(text=full_text, metadata=metadata))

            else:
                # Return each page as separate document
                for page_num in range(num_pages):
                    page_text = pdf.pages[page_num].extract_text()
                    page_label = pdf.page_labels[page_num] if hasattr(pdf, 'page_labels') else str(page_num + 1)

                    metadata = {
                        "page_label": page_label, 
                        "file_name": file.name,
                        "page_number": page_num + 1,
                        "images_on_page": len(image_info_by_page[page_num]) if page_num < len(image_info_by_page) else 0
                    }
                    if extra_info is not None:
                        metadata.update(extra_info)

                    # Combine text and image captions for this page
                    content_parts = []
                    
                    if page_text.strip():
                        content_parts.append(page_text)
                    
                    # Add image captions
                    if page_num in captions_by_page:
                        content_parts.append("\n[IMAGES ON THIS PAGE]")
                        for caption in captions_by_page[page_num]:
                            content_parts.append(f"- {caption}")
                        content_parts.append("[END IMAGES]")

                    final_text = "\n".join(content_parts) if content_parts else ""
                    docs.append(Document(text=final_text, metadata=metadata))

            return docs

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Synchronous wrapper for load_data_async."""
        return asyncio.run(self.load_data_async(file, extra_info, fs))


# Test function
async def test_enhanced_pdf_reader():
    """Test the enhanced PDF reader."""
    pdf_path = Path(__file__).parent.parent.parent / "test_docs" / "abhilasha_6_april_ticket.pdf"
    
    if not pdf_path.exists():
        print(f"Test PDF not found: {pdf_path}")
        return
    
    print(f"Testing Enhanced PDF Reader with: {pdf_path.name}")
    
    # Initialize reader
    reader = EnhancedPDFReader(
        return_full_document=False,  # Get page-by-page results
        enable_image_captioning=True,
        enable_fast_image_detection=True
    )
    
    try:
        # Load and process the PDF
        documents = await reader.load_data_async(pdf_path)
        
        print(f"\n{'='*60}")
        print(f"ENHANCED PDF READER RESULTS") 
        print(f"{'='*60}")
        print(f"Total documents: {len(documents)}")
        
        for i, doc in enumerate(documents):
            print(f"\nDocument {i+1}:")
            print(f"  Metadata: {doc.metadata}")
            print(f"  Text length: {len(doc.text)} characters")
            
            if doc.text.strip():
                preview = doc.text[:300].replace('\n', ' ').strip()
                print(f"  Text preview: {preview}...")
            else:
                print(f"  No text content")
        
        return documents
        
    except Exception as e:
        print(f"Error testing enhanced PDF reader: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_enhanced_pdf_reader()) 