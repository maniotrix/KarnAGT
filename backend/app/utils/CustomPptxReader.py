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
import asyncio

from openai import AsyncOpenAI
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
from agents import Agent, Runner

def get_default_caption_agent(model_name: str = "gpt-4o"):
    return Agent(
        name="Caption Agent",
        model=model_name,  # Fix: Specify the model explicitly
        instructions="You are an expert at describing images from PowerPoint presentations. Describe images concisely, focusing on key visual elements, text, charts, or diagrams.",
    )

class OpenAIPptxReader(BaseReader):
    """
    Powerpoint parser.

    Extract text, caption images, and specify slides.

    """

    def __init__(
        self, 
        api_key: Optional[str] = None,
        enable_logging: bool = False,
        enable_delay: bool = False,
        model_name: str = "gpt-4o"
    ) -> None:
        """Init parser with configurable OpenAI client."""
        try:
            from pptx import Presentation  # noqa
        except ImportError:
            raise ImportError(
                "Please install python-pptx: `pip install python-pptx`"
            )

        # Use OpenAI client instead of heavy models
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.enable_logging = enable_logging
        self.caption_agent = get_default_caption_agent(model_name)
        self.enable_delay = enable_delay
        
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
            self.logger.info(f"OpenAIPptxReader initialized with model: {self.caption_agent.model}")

    async def caption_image(self, tmp_image_file: str) -> str:
        """Generate text caption of image using OpenAI Vision."""
        temp_openai_file_id = None
        
        try:
            if self.enable_logging:
                self.logger.debug(f"Processing image file: {tmp_image_file}")
                
            # Upload to OpenAI Files API
            with open(tmp_image_file, 'rb') as f:
                file_response = await self.client.files.create(
                    file=f,
                    purpose="vision"
                )
                temp_openai_file_id = file_response.id
            
            if self.enable_logging:
                self.logger.debug(f"Uploaded to OpenAI with file_id: {temp_openai_file_id}")
            
            # Add timeout to prevent hanging
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
            if self.enable_logging:
                self.logger.debug(f"Vision API response: {result}")
            
            return result
            
        except asyncio.TimeoutError:
            if self.enable_logging:
                self.logger.error(f"Timeout processing image: {tmp_image_file}")
            return "Error: Image processing timed out after 60 seconds"
        except Exception as e:
            if self.enable_logging:
                self.logger.error(f"Error processing image: {str(e)}")
            return f"Error processing image: {str(e)}"
            
        finally:
            # Cleanup: Delete OpenAI file
            if temp_openai_file_id:
                try:
                    await self.client.files.delete(temp_openai_file_id)
                    if self.enable_logging:
                        self.logger.debug(f"Deleted OpenAI file: {temp_openai_file_id}")
                except Exception as e:
                    if self.enable_logging:
                        self.logger.warning(f"Failed to delete OpenAI file {temp_openai_file_id}: {e}")

    async def aload_data(
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
                        
                        # Add delay to avoid rate limiting if this isn't the first image
                        if total_images > 0 and self.enable_delay:
                            if self.enable_logging:
                                self.logger.debug(f"Adding 2s delay before processing image {total_images + 1}")
                            await asyncio.sleep(2.0)  # 2-second delay between images
                        
                        caption = await self.caption_image(f.name)
                        result += f"\n Image: {caption}\n\n"
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
