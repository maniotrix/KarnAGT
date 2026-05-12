#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test: Pytesseract OCR inside CodeSandbox workspace
This minimal test verifies that the remote execution environment has
pytesseract (and its Tesseract runtime) correctly configured by
creating a synthetic image with the word "HELLO" and extracting it
using pytesseract.
"""

import asyncio
import os
import sys
from typing import Any

from dotenv import load_dotenv

# Load environment variables (if any)
load_dotenv()

# Add the backend folder to sys.path so test runner can import project code
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
sys.path.append(BACKEND_DIR)

# Local imports (after mutating sys.path)
from app.aicore.code_executor.services import (
    WorkspaceService,
    ExecutionService,
)
from app.aicore.code_executor.models import ExecutionOperationResult


class _Logger:  # simple inline logger to keep output similar to other tests
    def __init__(self) -> None:
        self.logs = []

    def info(self, msg: str, **kwargs: Any) -> None:
        entry = f"[INFO] {msg}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)

    def error(self, msg: str, **kwargs: Any) -> None:
        entry = f"[ERROR] {msg}"
        if kwargs:
            entry += f" | {kwargs}"
        self.logs.append(entry)
        print(entry)


# Python code that will run inside the CodeSandbox workspace.
# It synthesises an image containing the text "HELLO" and then
# uses pytesseract to read it back. The recognised text is returned
# as the execution result.
OCR_CODE = """
import numpy as np
import cv2
import pytesseract

print("🔧 Creating synthetic image with 'HELLO' text...")

# Create a blank white image
img = np.ones((100, 400, 3), dtype=np.uint8) * 255  # white background
# Put the word 'HELLO' in black letters
cv2.putText(img, 'HELLO', (5, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3, cv2.LINE_AA)

print("🔍 Running OCR with pytesseract...")

# Perform OCR
text = pytesseract.image_to_string(img)

print('🔍 OCR OUTPUT:', repr(text))
print('🔍 OCR OUTPUT (stripped):', repr(text.strip()))

# Return the stripped text as the result
result = text.strip()
result
"""


async def _create_workspace(logger: _Logger):
    logger.info("Creating workspace…")
    ws_service = WorkspaceService()
    ws_result = await ws_service.create_workspace()
    if not ws_result.success or ws_result.workspace_info is None:
        logger.error("Workspace creation failed", error=ws_result.error)
        raise RuntimeError("Workspace creation failed")
    logger.info("Workspace created", workspace_id=ws_result.workspace_info.workspace_id)
    return ws_service, ws_result.workspace_info.workspace_id


async def _cleanup_workspace(ws_service: WorkspaceService, workspace_id: str, logger: _Logger):
    logger.info("Cleaning up workspace", workspace_id=workspace_id)
    try:
        await ws_service.delete_workspace(workspace_id)
    except Exception as exc:  # pragma: no cover – cleanup must never fail the suite
        logger.error("Workspace cleanup failed", error=str(exc))


async def test_pytesseract_ocr():
    """Main asynchronous test entrypoint."""
    logger = _Logger()

    # 1. Create a workspace
    ws_service, workspace_id = await _create_workspace(logger)

    # 2. Execute OCR code in that workspace
    logger.info("Executing OCR code…")
    exec_service = ExecutionService()
    exec_result: ExecutionOperationResult = await exec_service.execute_code(workspace_id, OCR_CODE)

    try:
        assert exec_result.success, f"Code execution failed: {exec_result.error}"
        assert exec_result.execution_result is not None, "No execution result returned"

        # Debug: Print all available output
        logger.info("Execution stdout", stdout=exec_result.execution_result.stdout)
        logger.info("Execution stderr", stderr=exec_result.execution_result.stderr)
        logger.info("Result data", result_data=exec_result.execution_result.result_data)

        # Check if we have result_data or need to parse stdout
        if exec_result.execution_result.result_data is not None:
            recognised_text = str(exec_result.execution_result.result_data)
        else:
            # Fallback: extract from stdout if result_data is None
            stdout = exec_result.execution_result.stdout
            assert stdout, "No stdout output available"
            # Look for the OCR OUTPUT line
            for line in stdout.split('\n'):
                if '🔍 OCR OUTPUT:' in line:
                    recognised_text = line.split('🔍 OCR OUTPUT:')[1].strip()
                    break
            else:
                # If no specific OCR output line, use the whole stdout
                recognised_text = stdout.strip()

        logger.info("Final recognised text", text=recognised_text)
        
        assert isinstance(recognised_text, str), f"Result is not a string: {type(recognised_text)}"
        # Normalise whitespace/newlines for robust comparison
        cleaned_text = recognised_text.strip().upper().replace("\n", " ")
        assert "HELLO" in cleaned_text, f"Expected 'HELLO' in OCR output, got: '{cleaned_text}'"

    finally:
        # Always attempt workspace cleanup, even if assertions fail
        await _cleanup_workspace(ws_service, workspace_id, logger)


if __name__ == "__main__":
    # Allow running the test directly for quick manual verification
    asyncio.run(test_pytesseract_ocr())
