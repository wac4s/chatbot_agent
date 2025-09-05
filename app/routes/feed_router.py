# app/routes/feed_router.py for explore page
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Photo, Video, User
from fastapi.templating import Jinja2Templates
from sqlalchemy import desc
import heapq
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/explore")
def explore_page(request: Request, db: Session = Depends(get_db)):
    # Fetch recent photos and videos separately
    recent_photos = db.query(Photo).order_by(desc(Photo.created_at)).limit(40).all()
    recent_videos = db.query(Video).order_by(desc(Video.created_at)).limit(40).all()

    # Merge by created_at descending and take top 20
    merged = heapq.nlargest(
        20,
        recent_photos + recent_videos,
        key=lambda m: m.created_at or datetime.min,
    )

    return templates.TemplateResponse(
        "explore.html",
        {
            "request": request,
            "media_list": merged,
            # Optional: if your template uses these sections, you can populate later
            # "hashtags": [],
            # "top_users": [],
        },
    )
