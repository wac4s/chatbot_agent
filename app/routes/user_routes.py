# Create Follow Endpoint
# routes/user_routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User

router = APIRouter()


@router.post("/follow/{target_user_id}")
def follow_user(target_user_id: int, current_user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(current_user_id)
    target_user = db.query(User).get(target_user_id)

    if not user or not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user in user.following:
        return {"message": "Already following"}

    user.following.append(target_user)
    db.commit()

    return {"message": f"{user.username} is now following {target_user.username}"}

# add notification
if media.user_id != current_user.id:  # Avoid self-notification
    create_notification(
        db=db,
        recipient_id=media.user_id,
        sender_id=current_user.id,
        message=f"{current_user.username} liked your post"
    )

# follow logic
create_notification(
    db,
    recipient_id=user_to_follow.id,
    sender_id=current_user.id,
    message=f"{current_user.username} followed you"

# View Followers / Following
@router.get("/user/{user_id}/followers")
def get_followers(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    return {"followers": [u.username for u in user.followers]}

@router.get("/user/{user_id}/following")
def get_following(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    return {"following": [u.username for u in user.following]}

# Show Videos Only from Followed Users
@router.get("/feed")
def get_feed(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(user_id)
    followed_users = [u.id for u in user.following]

    videos = db.query(Video).filter(Video.user_id.in_(followed_users)).all()
    return videos

# Add register, login, logout, and get current user:
# app/routes/user_routes.py
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.auth import hash_password, verify_password, create_session, read_session
from app.main import templates

router = APIRouter()

def get_current_user(request: Request, db: Session):
    session_token = request.cookies.get("session_token")
    user_id = read_session(session_token)
    if user_id:
        return db.query(User).get(user_id)
    return None

@router.get("/register")
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@router.post("/register")
def register_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    if db.query(User).filter_by(username=username).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username taken"})

    user = User(username=username, password=hash_password(password))
    db.add(user)
    db.commit()
    response = RedirectResponse("/login", status_code=302)
    return response

@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter_by(username=username).first()
    if not user or not verify_password(password, user.password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

    token = create_session(user.id)
    response = RedirectResponse("/feed", status_code=302)
    response.set_cookie(key="session_token", value=token, httponly=True)
    return response

@router.get("/logout")
def logout(request: Request):
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("session_token")
    return response

# add Follow / Unfollow / Profile routes
from fastapi import Path
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import joinedload

@router.get("/user/{user_id}", response_class=HTMLResponse)
def view_user_profile(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    target_user = db.query(User).options(joinedload(User.followers), joinedload(User.following)).get(user_id)
    current_user = get_current_user(request, db)

    if not target_user:
        return templates.TemplateResponse("base.html", {"request": request, "content": "User not found"})

    is_following = False
    if current_user and target_user in current_user.following:
        is_following = True

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": target_user,
        "current_user": current_user,
        "is_following": is_following
    })

@router.post("/follow/{target_user_id}")
def follow_user(
    target_user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    target_user = db.query(User).get(target_user_id)

    if not current_user or not target_user:
        return RedirectResponse(url="/login", status_code=302)

    if target_user not in current_user.following:
        current_user.following.append(target_user)
        db.commit()

    return RedirectResponse(f"/user/{target_user_id}", status_code=302)

@router.post("/unfollow/{target_user_id}")
def unfollow_user(
    target_user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    target_user = db.query(User).get(target_user_id)

    if not current_user or not target_user:
        return RedirectResponse(url="/login", status_code=302)

    if target_user in current_user.following:
        current_user.following.remove(target_user)
        db.commit()

    return RedirectResponse(f"/user/{target_user_id}", status_code=302)

# Profile Edit Route
import os

AVATAR_DIR = "static/uploads"
os.makedirs(AVATAR_DIR, exist_ok=True)

@router.get("/profile/edit")
def edit_profile_form(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)
    return templates.TemplateResponse("edit_profile.html", {"request": request, "current_user": user})

@router.post("/profile/edit")
def edit_profile_submit(
    request: Request,
    bio: str = Form(""),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=302)

    user.bio = bio

    if avatar and avatar.filename:
        avatar_path = os.path.join(AVATAR_DIR, avatar.filename)
        with open(avatar_path, "wb") as f:
            f.write(avatar.file.read())
        user.avatar = avatar.filename

    db.commit()
    return RedirectResponse(f"/user/{user.id}", status_code=302)

# add route for notifications
{% extends "base.html" %}
{% block title %}Notifications{% endblock %}
{% block content %}
<h2>Notifications</h2>
<ul>
  {% for note in notifications %}
    <li {% if not note.read %}style="font-weight:bold"{% endif %}>
      {{ note.message }} <small>({{ note.timestamp.strftime('%Y-%m-%d %H:%M') }})</small>
    </li>
  {% endfor %}
</ul>
{% endblock %}

# Block User Button on Profile - route
@router.post("/block/{target_id}")
def block_user(target_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    target = db.query(User).get(target_id)
    if user and target and target not in user.blocked:
        user.blocked.append(target)
        db.commit()
    return RedirectResponse(f"/user/{target_id}", status_code=302)

@router.post("/unblock/{target_id}")
def unblock_user(target_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    target = db.query(User).get(target_id)
    if user and target and target in user.blocked:
        user.blocked.remove(target)
        db.commit()
    return RedirectResponse(f"/user/{target_id}", status_code=302)

# app/routers/user_router.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/user/{user_id}")
def user_profile(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse("/")

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user_profile": user,
        "media": user.media,
        "followers": len(user.followers),
        "following": len(user.following),
        "total_likes": sum(len(m.likes) for m in user.media)
    })

# Add Notification Hooks
from app.utils.notifications import create_notification

# Show notifications to users
@router.get("/notifications")
def view_notifications(request: Request, db: Session = Depends(get_db)):
    current_user = db.query(User).first()  # 🔒 Replace with real current user
    notifs = db.query(Notification).filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return templates.TemplateResponse("notifications.html", {
        "request": request,
        "notifications": notifs
    })

