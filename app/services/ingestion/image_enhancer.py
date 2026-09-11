import cv2
import numpy as np
from skimage.filters import threshold_sauvola
from pathlib import Path

class ImageEnhancerService:
    @staticmethod
    def enhance(image_path: str) -> str:
        """Tiền xử lý ảnh: deskew -> bilateral filter -> CLAHE -> Sauvola."""
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError("Không thể đọc ảnh")

        img = ImageEnhancerService.deskew(img)
        img = cv2.bilateralFilter(img, 9, 75, 75)
        img = ImageEnhancerService.apply_clahe(img)
        img = ImageEnhancerService.apply_sauvola(img)
        
        path_obj = Path(image_path)
        out_path = path_obj.parent / f"enhanced_{path_obj.name}"
        cv2.imwrite(str(out_path), img)
        return str(out_path)

    @staticmethod
    def deskew(image: np.ndarray) -> np.ndarray:
        """Phát hiện độ nghiêng và xoay ảnh (Deskew)."""
        coords = np.column_stack(np.where(image > 0))
        if len(coords) == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    @staticmethod
    def apply_clahe(image: np.ndarray) -> np.ndarray:
        """Tăng cường độ tương phản cục bộ."""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    @staticmethod
    def apply_sauvola(image: np.ndarray) -> np.ndarray:
        """Nhị phân hóa ảnh bằng Sauvola."""
        window_size = 25
        thresh_sauvola = threshold_sauvola(image, window_size=window_size)
        binary_sauvola = image > thresh_sauvola
        return (binary_sauvola * 255).astype(np.uint8)
