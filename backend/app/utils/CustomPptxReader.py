"""
Slides parser.

Contains parsers for .pptx files.

"""

import io
import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional
from fsspec import AbstractFileSystem

from openai import OpenAI
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document


class OpenAIPptxReader(BaseReader):
    """
    Powerpoint parser.

    Extract text, caption images, and specify slides.

    """

    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4o",
        system_prompt: str = "You are an expert at describing images from PowerPoint presentations. Describe images concisely, focusing on key visual elements, text, charts, or diagrams.",
        enable_logging: bool = False
    ) -> None:
        """Init parser with configurable OpenAI client."""
        try:
            from pptx import Presentation  # noqa
        except ImportError:
            raise ImportError(
                "Please install python-pptx: `pip install python-pptx`"
            )

        # Use OpenAI client instead of heavy models
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.system_prompt = system_prompt
        self.enable_logging = enable_logging
        
        # Setup logger
        self.logger = logging.getLogger(__name__)
        if self.enable_logging:
            # Configure logger properly - this is likely the issue
            self.logger.setLevel(logging.DEBUG)
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                handler.setLevel(logging.DEBUG)
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            self.logger.info(f"OpenAIPptxReader initialized with model: {model}")

    def caption_image(self, tmp_image_file: str) -> str:
        """Generate text caption of image using OpenAI Vision."""
        temp_openai_file_id = None
        
        try:
            if self.enable_logging:
                self.logger.debug(f"Processing image file: {tmp_image_file}")
                
            # Upload to OpenAI Files API
            with open(tmp_image_file, 'rb') as f:
                file_response = self.client.files.create(
                    file=f,
                    purpose="vision"
                )
                temp_openai_file_id = file_response.id
            
            if self.enable_logging:
                self.logger.debug(f"Uploaded to OpenAI with file_id: {temp_openai_file_id}")
            
            # Process with vision model
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_prompt},
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
            )
            
            result = response.output_text.strip()
            if self.enable_logging:
                self.logger.debug(f"Vision API response: {result}")
            
            return result
            
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Error processing image: {str(e)}")
            return f"Error processing image: {str(e)}"
            
        finally:
            # Cleanup: Delete OpenAI file
            if temp_openai_file_id:
                try:
                    self.client.files.delete(temp_openai_file_id)
                    if self.enable_logging:
                        self.logger.debug(f"Deleted OpenAI file: {temp_openai_file_id}")
                except Exception as e:
                    if self.enable_logging:
                        self.logger.warning(f"Failed to delete OpenAI file {temp_openai_file_id}: {e}")

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Parse file."""
        from pptx import Presentation

        if self.enable_logging:
            self.logger.info(f"Loading PowerPoint file: {file}")

        if fs:
            with fs.open(str(file)) as f:
                presentation = Presentation(io.BytesIO(f.read()))
        else:
            presentation = Presentation(file)
        
        result = ""
        total_images = 0
        
        for i, slide in enumerate(presentation.slides):
            if self.enable_logging:
                self.logger.debug(f"Processing slide {i + 1}")
            
            result += f"\n\nSlide #{i}: \n"
            slide_images = 0
            
            for shape in slide.shapes:
                if hasattr(shape, "image"):
                    image = shape.image
                    # get image "file" contents
                    image_bytes = image.blob
                    # temporarily save the image to feed into model
                    f = tempfile.NamedTemporaryFile("wb", delete=False, suffix=".png")
                    try:
                        f.write(image_bytes)
                        f.close()
                        result += f"\n Image: {self.caption_image(f.name)}\n\n"
                        slide_images += 1
                        total_images += 1
                    finally:
                        os.unlink(f.name)

                if hasattr(shape, "text"):
                    result += f"{shape.text}\n"
            
            if self.enable_logging and slide_images > 0:
                self.logger.debug(f"Slide {i + 1} contained {slide_images} images")

        if self.enable_logging:
            self.logger.info(f"Completed processing: {len(presentation.slides)} slides, {total_images} images")

        return [Document(text=result, metadata=extra_info or {})]
