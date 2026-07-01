"""
=============================================================================
Model Service - CNN Detection API
=============================================================================
Service chính cho việc load và chạy inference các model CNN Detection.

Hỗ trợ 4 loại model:
  1. ResNet50 single-stream (paper gốc)
  2. DualStreamCNN
  3. DualStreamCNNEnhanced (với CBAM Attention)
  4. DualStreamResNet (ResNet18 backbone)

Sử dụng Singleton pattern — model được cache sau lần load đầu tiên.
"""

import os
import sys
import logging
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn.functional as F
from PIL import Image

from app.config import (
    get_settings,
    VALID_MODEL_TYPES,
    MODEL_WEIGHT_PATHS,
)
from chatbot.utils.image_processing import (
    preprocess_image,
    compute_fft_spectrum_gui
)

logger = logging.getLogger(__name__)

# Thêm đường dẫn project gốc (CNNDetection) vào sys.path để import networks
_PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class ModelService:
    """
    Service quản lý và chạy inference các model CNN Detection
    Attributes:
        _models: Cache các model đã load {model_type: model}.
        _device: Thiết bị tính toán (CPU/CUDA).

    Example:
        >>> service = ModelService()
        >>> result = service.predict(pil_image, "dual_stream_enhanced")
        >>> print(result["probability"])
    """

    def __init__(self):
        """Khởi tạo ModelService."""
        self._models: Dict[str, torch.nn.Module] = {}
        self._device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        logger.info("ModelService initialized. Device: %s", self._device)

    @property
    def device(self) -> torch.device:
        """Thiết bị tính toán hiện tại."""
        return self._device

    @property
    def loaded_models(self) -> List[str]:
        """Danh sách các model đã load."""
        return list(self._models.keys())

    def _get_weights_path(self, model_type: str) -> str:
        """
        Lấy đường dẫn tuyệt đối tới file weights.

        Args:
            model_type: Loại model.

        Returns:
            str: Đường dẫn tuyệt đối.

        Raises:
            FileNotFoundError: Nếu file weights không tồn tại.
        """
        settings = get_settings()
        weights_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", settings.WEIGHTS_DIR)
        )
        relative_path = MODEL_WEIGHT_PATHS.get(model_type)
        if not relative_path:
            raise ValueError(f"Không có weight path cho model type: {model_type}")

        full_path = os.path.join(weights_dir, relative_path)
        if not os.path.isfile(full_path):
            raise FileNotFoundError(
                f"Không tìm thấy weights: {full_path}"
            )
        return full_path

    def _load_checkpoint(self, model_path: str) -> dict:
        """
        Load checkpoint từ file.

        Args:
            model_path: Đường dẫn file .pth.

        Returns:
            dict: Checkpoint data.
        """
        return torch.load(model_path, map_location="cpu", weights_only=False)

    def _load_state_dict(self, model: torch.nn.Module, checkpoint: dict) -> None:
        """
        Load state_dict vào model, hỗ trợ cả format {'model': ...} và flat.

        Args:
            model: PyTorch model instance.
            checkpoint: Checkpoint dict.
        """
        if "model" in checkpoint:
            model.load_state_dict(checkpoint["model"])
        else:
            model.load_state_dict(checkpoint)

    def load_model(self, model_type: str) -> torch.nn.Module:
        """
        Load model theo type. Cache lại sau lần load đầu tiên.

        Args:
            model_type: Một trong VALID_MODEL_TYPES.

        Returns:
            torch.nn.Module: Model đã load và sẵn sàng inference.

        Raises:
            ValueError: Nếu model_type không hợp lệ.
            FileNotFoundError: Nếu weights không tồn tại.
        """
        if model_type not in VALID_MODEL_TYPES:
            raise ValueError(
                f"Model type '{model_type}' không hợp lệ. "
                f"Chọn: {VALID_MODEL_TYPES}"
            )

        # Trả về cached model nếu có
        if model_type in self._models:
            return self._models[model_type]

        weights_path = self._get_weights_path(model_type)
        checkpoint = self._load_checkpoint(weights_path)
        logger.info("Loading model '%s' from: %s", model_type, weights_path)

        if model_type == "resnet50":
            model = self._load_resnet50(checkpoint)
        elif model_type == "dual_stream":
            model = self._load_dual_stream_cnn(checkpoint)
        elif model_type == "dual_stream_enhanced":
            model = self._load_dual_stream_enhanced(checkpoint)
        elif model_type == "dual_stream_resnet":
            model = self._load_dual_stream_resnet(checkpoint)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        model = model.to(self._device)
        model.eval()
        self._models[model_type] = model
        logger.info("Model '%s' loaded successfully. Device: %s", model_type, self._device)
        return model

    def _load_resnet50(self, checkpoint: dict) -> torch.nn.Module:
        """Load ResNet50 single-stream model."""
        from networks.resnet import resnet50
        model = resnet50(num_classes=1)
        self._load_state_dict(model, checkpoint)
        return model

    def _load_dual_stream_cnn(self, checkpoint: dict) -> torch.nn.Module:
        """Load DualStreamCNN model."""
        from networks.dual_stream_cnn import DualStreamCNN
        model = DualStreamCNN(num_classes=1, dropout=0.5)
        self._load_state_dict(model, checkpoint)
        return model

    def _load_dual_stream_enhanced(self, checkpoint: dict) -> torch.nn.Module:
        """Load DualStreamCNNEnhanced model."""
        from networks.dual_stream_enhanced import DualStreamCNNEnhanced
        model = DualStreamCNNEnhanced(num_classes=1, dropout=0.5)
        self._load_state_dict(model, checkpoint)
        return model

    def _load_dual_stream_resnet(self, checkpoint: dict) -> torch.nn.Module:
        """Load DualStreamResNet model."""
        from networks.dual_stream_resnet import DualStreamResNet
        model = DualStreamResNet(num_classes=1, dropout=0.5)
        self._load_state_dict(model, checkpoint)
        return model

    def predict(self, image: Image.Image, model_type: Optional[str] = None) -> dict:
        """
        Chạy inference trên 1 ảnh.

        Args:
            image: Ảnh PIL (RGB).
            model_type: Loại model. Mặc định từ config.

        Returns:
            dict: Kết quả prediction:
                - probability (float): Xác suất fake (0.0 - 1.0)
                - percentage (str): Xác suất dạng %
                - label (str): "real" hoặc "fake"
                - confidence (str): Độ tin cậy dạng %
                - model_used (str): Model type đã dùng

        Raises:
            ValueError: Nếu model_type không hợp lệ.
            RuntimeError: Nếu inference thất bại.
        """
        settings = get_settings()
        model_type = model_type or settings.DEFAULT_MODEL_TYPE

        # Load model (cached)
        model = self.load_model(model_type)

        # Preprocess
        rgb_tensor = preprocess_image(image, model_type).to(self._device)

        # Inference
        fft_base64 = None
        with torch.no_grad():
            if model_type == "resnet50":
                logits = model(rgb_tensor)
            else:
                # Dual-stream: cần thêm FFT input
                fft_tensor = self._compute_fft_for_model(image, model_type)
                logits = model(rgb_tensor, fft_tensor)
                fft_base64 = self._tensor_to_base64(fft_tensor)

            probability = torch.sigmoid(logits).squeeze().item()

        # Format result
        label = "fake" if probability >= 0.5 else "real"
        confidence = probability if probability >= 0.5 else (1.0 - probability)

        return {
            "probability": round(probability, 6),
            "percentage": f"{probability * 100:.2f}%",
            "label": label,
            "confidence": f"{confidence * 100:.2f}%",
            "model_used": model_type,
            "fft_base64": fft_base64,
        }

    def predict_batch(
        self,
        images: List[Image.Image],
        model_type: Optional[str] = None
    ) -> List[dict]:
        """
        Chạy inference trên nhiều ảnh.

        Args:
            images: Danh sách ảnh PIL.
            model_type: Loại model.

        Returns:
            List[dict]: Danh sách kết quả prediction.
        """
        return [self.predict(img, model_type) for img in images]

    def _compute_fft_for_model(
        self, image: Image.Image, model_type: str
    ) -> torch.Tensor:
        """
        Tính FFT spectrum phù hợp với từng loại model theo gui_dark_pro.py
        """
        fft = compute_fft_spectrum_gui(image, model_type)
        return fft.to(self._device)

    def _tensor_to_base64(self, tensor: torch.Tensor) -> str:
        import base64
        from io import BytesIO
        import torchvision.transforms as T
        
        # Tensor is (1, C, H, W)
        tensor = tensor.detach().cpu().squeeze(0) # (C, H, W)
        
        # Normalize to 0-1
        t_min = tensor.min()
        t_max = tensor.max()
        if t_max > t_min:
            tensor = (tensor - t_min) / (t_max - t_min)
            
        img_pil = T.ToPILImage()(tensor)
        buffered = BytesIO()
        img_pil.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
_model_service: Optional[ModelService] = None


def get_model_service() -> ModelService:
    """
    Lấy singleton ModelService instance.

    Returns:
        ModelService: Instance duy nhất.
    """
    global _model_service
    if _model_service is None:
        _model_service = ModelService()
    return _model_service
