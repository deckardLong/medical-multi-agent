import cv2

MIN_SIDE = 800
MIN_SHARPNESS = 100.0

def check_image(path: str) -> str | None:
    """None = đạt; chuỗi = lý do từ chối. Ảnh kém thì 3 agent cùng đọc sai giống nhau, đồng thuận lúc đó vô nghĩa."""
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        return "Không mở được file ảnh"
    if min(img.shape[:2]) < MIN_SIDE:
        return f"Ảnh quá nhỏ ({img.shape[1]}x{img.shape[0]}px), cần cạnh ngắn ≥ {MIN_SIDE}px"
    if cv2.Laplacian(img, cv2.CV_64F).var() < MIN_SHARPNESS:
        return "Ảnh bị mờ, hãy chụp lại rõ nét, đủ sáng"
    return None