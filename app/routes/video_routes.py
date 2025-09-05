# User Feed + Upload Video System
# app/routes/video_routes.py
from fastapi import APIRouter, Request, UploadFile, File, Depends, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Video
from app.routes.user_routes import get_current_user
from app.main import templates
import os
import shutil

UPLOAD_DIR = "app/static/uploads"

router = APIRouter()

@router.get("/upload")
def upload_form(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("upload.html", {"request": request})

@router.post("/upload")
def upload_video(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    video = Video(filename=file.filename, user_id=current_user.id)
    db.add(video)
    db.commit()

    return RedirectResponse("/feed", status_code=302)

# add photo routes
    import mimetypes

    file_type, _ = mimetypes.guess_type(file.filename)

    if file_type and file_type.startswith("image"):
    # treat as photo
    else:
    # treat as video

    # add Update /upload route to save hashtags
    hashtags = []
    for tag in extract_hashtags(caption):
        existing = db.query(Hashtag).filter_by(name=tag.lower()).first()
        if existing:
            hashtags.append(existing)
        else:
            new_tag = Hashtag(name=tag.lower())
            db.add(new_tag)
            db.commit()
            hashtags.append(new_tag)

    if file_type and file_type.startswith("image"):
        photo = Photo(filename=file.filename, caption=caption, user_id=current_user.id, hashtags=hashtags)
        db.add(photo)
    else:
        video = Video(filename=file.filename, caption=caption, user_id=current_user.id, hashtags=hashtags)
        db.add(video)




@router.get("/feed")
def view_feed(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

# added here - block user
    blocked_ids = [u.id for u in current_user.blocked]
    followed_ids = [u.id for u in current_user.following] + [current_user.id]

    allowed_ids = list(set(followed_ids) - set(blocked_ids))

    videos = db.query(Video).filter(Video.user_id.in_(allowed_ids)).order_by(Video.id.desc()).all()
    photos = db.query(Photo).filter(Photo.user_id.in_(allowed_ids)).order_by(Photo.id.desc()).all()


    followed_ids = [u.id for u in current_user.following] + [current_user.id]
    videos = db.query(Video).filter(Video.user_id.in_(followed_ids)).order_by(Video.id.desc()).all()

    return templates.TemplateResponse("feed.html", {
        "request": request,
        "videos": videos,
        "current_user": current_user
    })

# Pagination for Feed
@router.get("/feed")
def view_feed(request: Request, page: int = 1, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    page_size = 5
    offset = (page - 1) * page_size

    followed_ids = [u.id for u in current_user.following] + [current_user.id]
    total_videos = db.query(Video).filter(Video.user_id.in_(followed_ids)).count()
    videos = db.query(Video).filter(Video.user_id.in_(followed_ids)).order_by(Video.id.desc()).offset(offset).limit(page_size).all()

    next_page = page + 1 if offset + page_size < total_videos else None
    prev_page = page - 1 if page > 1 else None

    return templates.TemplateResponse("feed.html", {
        "request": request,
        "videos": videos,
        "current_user": current_user,
        "next_page": next_page,
        "prev_page": prev_page
    })

# update video route
@router.post("/upload")
def upload_video(
    request: Request,
    file: UploadFile = File(...),
    caption: str = Form(""),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user:
        return RedirectResponse("/login", status_code=302)

    save_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    video = Video(filename=file.filename, caption=caption, user_id=current_user.id)
    db.add(video)
    db.commit()

    return RedirectResponse("/feed", status_code=302)

# Create Comment Routes
from app.models import Comment

@router.post("/comment/video/{video_id}")
def comment_on_video(
    video_id: int,
    request: Request,
    text: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    comment = Comment(text=text, user_id=user.id, video_id=video_id)
    db.add(comment)
    db.commit()

    return RedirectResponse("/feed", status_code=302)


@router.post("/comment/photo/{photo_id}")
def comment_on_photo(
    photo_id: int,
    request: Request,
    text: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    comment = Comment(text=text, user_id=user.id, photo_id=photo_id)
    db.add(comment)
    db.commit()

    return RedirectResponse("/feed", status_code=302)

# Add Hashtag Parsing Function
import re
from app.models import Hashtag

def extract_hashtags(caption: str):
    return re.findall(r"#(\w+)", caption or "")

# Add Hashtag Feed Route
@router.get("/hashtag/{tag}")
def view_hashtag(tag: str, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    hashtag = db.query(Hashtag).filter_by(name=tag.lower()).first()
    if not hashtag:
        return templates.TemplateResponse("feed.html", {
            "request": request,
            "videos": [],
            "photos": [],
            "current_user": current_user
        })

    return templates.TemplateResponse("feed.html", {
        "request": request,
        "videos": hashtag.videos,
        "photos": hashtag.photos,
        "current_user": current_user
    })

# Add a Search Route in video_routes.py
@router.get("/search")
def search_content(q: str, request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    if not q:
        return RedirectResponse("/feed", status_code=302)

    query = q.lower()

    matched_users = db.query(User).filter(User.username.ilike(f"%{query}%")).all()
    matched_photos = db.query(Photo).filter(Photo.caption.ilike(f"%{query}%")).all()
    matched_videos = db.query(Video).filter(Video.caption.ilike(f"%{query}%")).all()
    matched_hashtag = db.query(Hashtag).filter(Hashtag.name == query.strip("#")).first()

    if matched_hashtag:
        matched_photos += matched_hashtag.photos
        matched_videos += matched_hashtag.videos

    return templates.TemplateResponse("search.html", {
        "request": request,
        "query": q,
        "users": matched_users,
        "photos": matched_photos,
        "videos": matched_videos,
        "current_user": current_user
    })

# Build the Explore Page
from sqlalchemy import func

@router.get("/explore")
def explore_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)

    # Top 10 hashtags by count of associated photos + videos
    hashtag_counts = (
        db.query(Hashtag, func.count().label("total"))
        .outerjoin(photo_hashtag_association)
        .outerjoin(video_hashtag_association)
        .group_by(Hashtag.id)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )

    # Top 10 users by number of followers
    users = db.query(User).all()
    top_users = sorted(users, key=lambda u: len(u.followers), reverse=True)[:10]

    return templates.TemplateResponse("explore.html", {
        "request": request,
        "current_user": current_user,
        "hashtags": hashtag_counts,
        "top_users": top_users
    })

# Trigger Notifications
from app.utils.notifications import create_notification

# after liking
if user.id != video.user.id:
    create_notification(db, recipient_id=video.user.id, message=f"{user.username} liked your video.")

# Trigger notification on comment video
if user.id != video.user.id:
    create_notification(db, video.user.id, f"{user.username} commented on your video.")

# Trigger notification on comment photo
if user.id != photo.user.id:
    create_notification(db, photo.user.id, f"{user.username} commented on your photo.")

# on follow
if user.id != target_user.id:
    create_notification(db, target_user.id, f"{user.username} followed you.")

# Add moderator report route in video_routes.py
@router.post("/report")
def report_content(
    request: Request,
    type: str = Form(...),
    content_id: int = Form(...),
    reason: str = Form("Inappropriate"),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    report = Report(type=type, content_id=content_id, reason=reason, reporter_id=user.id)
    db.add(report)
    db.commit()

    return RedirectResponse("/feed", status_code=302)

