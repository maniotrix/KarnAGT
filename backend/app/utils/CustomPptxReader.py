"""
Slides parser.

Contains parsers for .pptx files.

"""

import io
import os
import tempfile
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
        system_prompt: str = "You are an expert at describing images from PowerPoint presentations. Describe images concisely, focusing on key visual elements, text, charts, or diagrams."
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

    def caption_image(self, tmp_image_file: str) -> str:
        """Generate text caption of image using OpenAI Vision."""
        temp_openai_file_id = None
        
        try:
            # Upload to OpenAI Files API
            with open(tmp_image_file, 'rb') as f:
                file_response = self.client.files.create(
                    file=f,
                    purpose="vision"
                )
                temp_openai_file_id = file_response.id
            
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
            
            return response.output_text.strip()
            
        except Exception as e:
            return f"Error processing image: {str(e)}"
            
        finally:
            # Cleanup: Delete OpenAI file
            if temp_openai_file_id:
                try:
                    self.client.files.delete(temp_openai_file_id)
                except Exception:
                    pass  # Ignore cleanup errors

    def load_data(
        self,
        file: Path,
        extra_info: Optional[Dict] = None,
        fs: Optional[AbstractFileSystem] = None,
    ) -> List[Document]:
        """Parse file."""
        from pptx import Presentation

        if fs:
            with fs.open(str(file)) as f:
                presentation = Presentation(io.BytesIO(f.read()))
        else:
            presentation = Presentation(file)
        result = ""
        for i, slide in enumerate(presentation.slides):
            result += f"\n\nSlide #{i}: \n"
            for shape in slide.shapes:
                if hasattr(shape, "image"):
                    image = shape.image
                    # get image "file" contents
                    image_bytes = image.blob
                    # temporarily save the image to feed into model
                    f = tempfile.NamedTemporaryFile("wb", delete=False)
                    try:
                        f.write(image_bytes)
                        f.close()
                        result += f"\n Image: {self.caption_image(f.name)}\n\n"
                    finally:
                        os.unlink(f.name)

                if hasattr(shape, "text"):
                    result += f"{shape.text}\n"

        return [Document(text=result, metadata=extra_info or {})]
