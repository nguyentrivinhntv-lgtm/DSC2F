import os
import gdown
import logging

logger = logging.getLogger(__name__)

# ID của các file weights trên Google Drive
WEIGHTS = {
    "blur_jpg_prob0.1.pth": "15l3F7g7JfCqYVajSOnEsBnySiRH3DEf-",
    "enhanced/best_model.pth": "1ObrE8GSEiAeIKm5KgPQbXfCjkbwKrLEM",
    "dual_stream_resnet/best_model.pth": "1BFToU2qaNmm6RWxywcCgl864OO1OBNxc"
}

def download_weights_if_needed():
    """Tải file weights từ Google Drive nếu chưa tồn tại cục bộ."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    weights_dir = os.path.join(base_dir, "weights")

    logger.info("Checking AI Models weights in: %s", weights_dir)

    for rel_path, file_id in WEIGHTS.items():
        file_path = os.path.join(weights_dir, rel_path)
        if not os.path.exists(file_path):
            logger.info("Weight file missing: %s. Downloading from Google Drive...", rel_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            url = f'https://drive.google.com/uc?id={file_id}'
            try:
                gdown.download(url, file_path, quiet=False)
                logger.info("Successfully downloaded: %s", rel_path)
            except Exception as e:
                logger.error("Failed to download %s from Google Drive: %s", rel_path, e)
                # Xóa file tạm nếu tải thất bại
                if os.path.exists(file_path):
                    os.remove(file_path)
        else:
            logger.info("Weight file already exists: %s", rel_path)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    download_weights_if_needed()
