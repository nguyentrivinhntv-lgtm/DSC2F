from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from app.security.security import get_current_user
from app.models.base_db import (
    get_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_read,
    delete_notification,
    create_notification,
    create_notification_broadcast,
    create_scheduled_notification,
    get_all_scheduled,
    delete_scheduled,
    get_user_by_username
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class SendNotificationRequest(BaseModel):
    title: str
    message: str
    type: str = 'info'
    target: str = 'all'

class ScheduleNotificationRequest(BaseModel):
    title: str
    message: str
    type: str = 'info'
    target: str = 'all'
    scheduled_times: list[str]

@router.get("/")
def api_get_notifications(limit: int = 20, offset: int = 0, current_user: dict = Depends(get_current_user)):
    return get_notifications(current_user["id"], limit=limit, offset=offset)

@router.get("/unread-count")
def api_get_unread_count(current_user: dict = Depends(get_current_user)):
    return {"count": get_unread_count(current_user["id"])}

@router.put("/{notification_id}/read")
def api_mark_read(notification_id: int, current_user: dict = Depends(get_current_user)):
    success = mark_notification_read(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo hoặc đã đọc.")
    return {"message": "Đã đánh dấu đã đọc."}

@router.put("/read-all")
def api_mark_all_read(current_user: dict = Depends(get_current_user)):
    count = mark_all_read(current_user["id"])
    return {"message": f"Đã đánh dấu {count} thông báo."}

@router.delete("/{notification_id}")
def api_delete_notification(notification_id: int, current_user: dict = Depends(get_current_user)):
    success = delete_notification(notification_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo.")
    return {"message": "Đã xóa thông báo."}

# ======================= ADMIN =======================

@router.post("/admin/send")
def api_admin_send_notification(req: SendNotificationRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    
    if req.target == 'all':
        count = create_notification_broadcast(req.title, req.message, req.type)
        msg = f"Đã gửi thông báo cho {count} người dùng."
    else:
        user = get_user_by_username(req.target)
        if not user:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy user '{req.target}'")
        create_notification(user['id'], req.title, req.message, req.type)
        msg = f"Đã gửi thông báo cho '{req.target}'"

    # Lưu vào lịch sử thông báo (scheduled_notifications nhưng đánh dấu đã gửi ngay lập tức)
    scheduled_id = create_scheduled_notification(
        title=req.title,
        message=req.message,
        ntype=req.type,
        target=req.target,
        scheduled_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        created_by=current_user["id"]
    )
    if scheduled_id:
        from app.models.base_db import mark_scheduled_sent
        mark_scheduled_sent(scheduled_id)

    return {"message": msg}

@router.post("/admin/schedule")
def api_admin_schedule_notification(req: ScheduleNotificationRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    
    count = 0
    for t in req.scheduled_times:
        create_scheduled_notification(
            title=req.title,
            message=req.message,
            ntype=req.type,
            target=req.target,
            scheduled_at=t,
            created_by=current_user["id"]
        )
        count += 1
    return {"message": f"Đã lên lịch {count} thông báo thành công."}

@router.get("/admin/scheduled")
def api_admin_get_scheduled(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    return get_all_scheduled()

@router.delete("/admin/scheduled/{scheduled_id}")
def api_admin_delete_scheduled(scheduled_id: int, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền thực hiện.")
    success = delete_scheduled(scheduled_id)
    if not success:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo hẹn giờ.")
    return {"message": "Đã xóa thông báo hẹn giờ."}
