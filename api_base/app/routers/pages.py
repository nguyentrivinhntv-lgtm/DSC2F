from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Optional

from app.models import base_db
from app.routers.auth import require_admin

router = APIRouter(prefix="/pages", tags=["Pages"])

class PageCreate(BaseModel):
    slug: str
    title: str
    title_en: Optional[str] = None
    content: str
    content_en: Optional[str] = None
    is_active: bool = True

class PageUpdate(BaseModel):
    title: str
    title_en: Optional[str] = None
    content: str
    content_en: Optional[str] = None
    is_active: bool = True

class PageResponse(BaseModel):
    id: int
    slug: str
    title: str
    title_en: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str

class PageDetailResponse(PageResponse):
    content: str
    content_en: Optional[str] = None

@router.get("", response_model=List[PageResponse])
def get_pages(is_admin: bool = False):
    """
    Lấy danh sách các trang. Public chỉ thấy trang active, Admin thấy tất cả.
    Lưu ý: Không trả về content để tối ưu băng thông.
    """
    try:
        # Nếu không có query param, mặc định public (chỉ lấy trang active)
        if is_admin:
            pages = base_db.get_all_pages()
        else:
            pages = base_db.get_active_pages()
        return pages
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{slug}", response_model=PageDetailResponse)
def get_page(slug: str, request: Request):
    """Lấy chi tiết một trang theo slug."""
    try:
        page = base_db.get_page_by_slug(slug)
        if not page:
            raise HTTPException(status_code=404, detail="Page not found")
        
        # Nếu trang bị vô hiệu hoá, chỉ admin mới nên xem
        if not page["is_active"]:
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=403, detail="Page is not active")
            
            token = auth_header.split(" ")[1]
            from app.security.security import decode_access_token
            try:
                payload = decode_access_token(token)
                user_id = payload.get("sub")
                if not user_id:
                    raise HTTPException(status_code=403, detail="Page is not active")
                user = base_db.get_user_by_id(int(user_id))
                if not user or user.get("role") != "admin":
                    raise HTTPException(status_code=403, detail="Page is not active")
            except Exception:
                raise HTTPException(status_code=403, detail="Page is not active")

        return page
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def create_page(page: PageCreate, admin_user: dict = Depends(require_admin)):
    """Tạo trang mới (Chỉ Admin)."""
    try:
        success = base_db.create_page(
            slug=page.slug,
            title=page.title,
            content=page.content,
            title_en=page.title_en,
            content_en=page.content_en,
            is_active=1 if page.is_active else 0
        )
        return {"message": "Tạo trang thành công"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{slug}")
def update_page(slug: str, page: PageUpdate, admin_user: dict = Depends(require_admin)):
    """Cập nhật trang (Chỉ Admin)."""
    try:
        # Kiểm tra tồn tại
        existing = base_db.get_page_by_slug(slug)
        if not existing:
            raise HTTPException(status_code=404, detail="Page not found")
            
        success = base_db.update_page(
            slug=slug,
            title=page.title,
            content=page.content,
            title_en=page.title_en,
            content_en=page.content_en,
            is_active=1 if page.is_active else 0
        )
        return {"message": "Cập nhật trang thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{slug}")
def delete_page(slug: str, admin_user: dict = Depends(require_admin)):
    """Xóa trang (Chỉ Admin)."""
    try:
        success = base_db.delete_page(slug)
        if not success:
            raise HTTPException(status_code=404, detail="Page not found")
        return {"message": "Xóa trang thành công"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
