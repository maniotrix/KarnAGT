from typing import Dict, Any
import time
import psutil
from dataclasses import dataclass

import psutil
import torch

@dataclass
class DeviceInfo:
    """System device information."""
    cpu_count: int
    cpu_freq: str
    memory_total: str
    gpu_info: str

class PerformanceMonitor:
    """Monitor and track performance metrics."""
    
    def __init__(self):
        self.timings: Dict[str, Dict[str, Any]] = {}
        self.device_info = self._get_device_info()
        
    def start_timing(self, operation: str) -> None:
        """Start timing an operation."""
        print(f"⏱️  Starting {operation}...")
        self.timings[operation] = {
            'start_time': time.time(),
            'cpu_before': psutil.cpu_percent(interval=0.1),
            'memory_before': psutil.virtual_memory().percent
        }
        
    def end_timing(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation not in self.timings:
            return 0.0
            
        timing = self.timings[operation]
        end_time = time.time()
        cpu_after = psutil.cpu_percent(interval=0.1)
        memory_after = psutil.virtual_memory().percent
        
        duration = end_time - timing['start_time']
        timing['duration'] = duration
        timing['cpu_after'] = cpu_after
        timing['memory_after'] = memory_after
        
        print(f"✅ {operation} completed in {duration:.3f}s")
        print(f"   📊 CPU: {timing['cpu_before']:.1f}% → {cpu_after:.1f}%")
        print(f"   💾 Memory: {timing['memory_before']:.1f}% → {memory_after:.1f}%")
        
        return duration
        
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        total_time = sum(t.get('duration', 0) for t in self.timings.values())
        return {
            'total_time': total_time,
            'operations': {k: v.get('duration', 0) for k, v in self.timings.items()}
        }
        
    def _get_device_info(self) -> DeviceInfo:
        """Get CPU and GPU information."""
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        
        gpu_info = "No GPU detected"
        if torch.cuda.is_available():
            gpu_info = f"GPU: {torch.cuda.get_device_name(0)} (CUDA Available)"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            gpu_info = "GPU: Apple Metal Performance Shaders (MPS)"
        
        return DeviceInfo(
            cpu_count=cpu_count,
            cpu_freq=f"{cpu_freq.current:.2f} MHz" if cpu_freq else "Unknown",
            memory_total=f"{memory.total / (1024**3):.2f} GB",
            gpu_info=gpu_info
        )
    
    def print_system_info(self) -> None:
        """Print system information."""
        print("🧪 Testing LlamaIndex RAG with different vector databases...")
        print("🖥️  System Information:")
        print(f"   cpu_count: {self.device_info.cpu_count}")
        print(f"   cpu_freq: {self.device_info.cpu_freq}")
        print(f"   memory_total: {self.device_info.memory_total}")
        print(f"   gpu_info: {self.device_info.gpu_info}")

        print()
    
