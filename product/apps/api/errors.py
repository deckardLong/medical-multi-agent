class ConflictError(ValueError):
    """Vi phạm quy tắc trạng thái (vd xác nhận lại mục đã xác nhận) → router trả 409; ValueError thường → 400."""
