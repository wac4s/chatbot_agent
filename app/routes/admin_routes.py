# Add Admin Delete Routes
@router.post("/admin/delete/video/{video_id}")
def delete_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.username != "admin":
        return RedirectResponse("/feed", status_code=302)

    video = db.query(Video).get(video_id)
    if video:
        db.delete(video)
        db.commit()

    return RedirectResponse("/admin/reports", status_code=302)

@router.post("/admin/delete/photo/{photo_id}")
def delete_photo(photo_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.username != "admin":
        return RedirectResponse("/feed", status_code=302)

    photo = db.query(Photo).get(photo_id)
    if photo:
        db.delete(photo)
        db.commit()

    return RedirectResponse("/admin/reports", status_code=302)

@router.post("/admin/delete/comment/{comment_id}")
def delete_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.username != "admin":
        return RedirectResponse("/feed", status_code=302)

    comment = db.query(Comment).get(comment_id)
    if comment:
        db.delete(comment)
        db.commit()

    return RedirectResponse("/admin/reports", status_code=302)


# Ban User by Username
@router.post("/admin/ban")
def ban_user_by_username(username: str = Form(...), request: Request = None, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.username != "admin":
        return RedirectResponse("/feed", status_code=302)

    user = db.query(User).filter_by(username=username).first()
    if user:
        # Optionally delete user's content
        db.query(Photo).filter_by(user_id=user.id).delete()
        db.query(Video).filter_by(user_id=user.id).delete()
        db.delete(user)
        db.commit()

    return RedirectResponse("/admin/reports", status_code=302)

