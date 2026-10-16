"""Published-snapshot search and private user collections."""

from datetime import date
from typing import Literal
import unicodedata
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from .auth import current_identity, Identity
from ai_service.taxonomy import Category
from .models import DailyReport, ReportItem
from .user_models import Bookmark, BookmarkTag, UserTag

router = APIRouter(tags=["search and collections"])


def search_condition(column, query):
    pattern = (
        "%" + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    )
    return or_(
        *(
            v.ilike(pattern, escape="\\")
            for v in (
                column["title"].as_string(),
                column["original_title"].as_string(),
                column["original_excerpt"].as_string(),
                column["analysis"]["summary"].as_string(),
            )
        )
    )


@router.get("/search")
def search(
    request: Request,
    q: str = Query("", max_length=100),
    region: Literal["china", "international"] | None = None,
    category: Category | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=50),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "开始日期不可晚于结束日期")
    query = select(
        ReportItem.snapshot.label("snapshot"),
        func.row_number()
        .over(partition_by=ReportItem.news_id, order_by=DailyReport.report_date.desc())
        .label("rank"),
    ).join(DailyReport)
    if q.strip():
        query = query.where(search_condition(ReportItem.snapshot, q.strip()))
    if region:
        query = query.where(ReportItem.region == region)
    if category:
        query = query.where(ReportItem.category == category)
    if date_from:
        query = query.where(DailyReport.report_date >= date_from)
    if date_to:
        query = query.where(DailyReport.report_date <= date_to)
    matches = query.subquery()
    result = select(matches.c.snapshot).where(matches.c.rank == 1)
    with request.app.state.factory() as db:
        total = db.scalar(select(func.count()).select_from(result.subquery()))
        rows = list(
            db.scalars(
                result.order_by(
                    matches.c.snapshot["report_date"].as_string().desc(),
                    matches.c.snapshot["id"].as_integer().desc(),
                )
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return {"items": rows, "total": total, "page": page, "page_size": page_size}


class TagInput(BaseModel):
    name: str = Field(min_length=1, max_length=24)

    @field_validator("name")
    @classmethod
    def normalize(cls, value):
        value = unicodedata.normalize("NFKC", value).strip()
        if (
            not value
            or len(value) > 24
            or any(unicodedata.category(c).startswith("C") for c in value)
        ):
            raise ValueError("标签须为 1–24 个可见字符")
        return value


class BookmarkInput(BaseModel):
    report_date: date | None = None
    tag_ids: list[int] | None = Field(default=None, max_length=20)


def tags_for(db, row):
    return [
        {"id": t.id, "name": t.name}
        for t in db.scalars(
            select(UserTag)
            .join(BookmarkTag)
            .where(BookmarkTag.bookmark_id == row.id, UserTag.user_id == row.user_id)
            .order_by(UserTag.id)
        )
    ]


def bookmark_dict(db, row):
    return {
        "news": row.snapshot,
        "saved_at": row.created_at.isoformat() + "Z",
        "tags": tags_for(db, row),
    }


@router.get("/tags")
def list_tags(request: Request, identity: Identity = Depends(current_identity)):
    with request.app.state.factory() as db:
        return [
            {"id": t.id, "name": t.name}
            for t in db.scalars(
                select(UserTag)
                .where(UserTag.user_id == identity.user_id)
                .order_by(UserTag.id)
            )
        ]


@router.post("/tags", status_code=201)
def create_tag(
    payload: TagInput, request: Request, identity: Identity = Depends(current_identity)
):
    try:
        with request.app.state.factory.begin() as db:
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
            if (
                db.scalar(
                    select(func.count())
                    .select_from(UserTag)
                    .where(UserTag.user_id == identity.user_id)
                )
                >= 100
            ):
                raise HTTPException(409, "最多创建 100 个标签")
            row = UserTag(
                user_id=identity.user_id,
                name=payload.name,
                name_key=payload.name.casefold(),
            )
            db.add(row)
            db.flush()
            return {"id": row.id, "name": row.name}
    except IntegrityError:
        raise HTTPException(409, "该标签已存在")


@router.patch("/tags/{tag_id}")
def rename_tag(
    tag_id: int,
    payload: TagInput,
    request: Request,
    identity: Identity = Depends(current_identity),
):
    try:
        with request.app.state.factory.begin() as db:
            row = db.get(UserTag, tag_id)
            if not row or row.user_id != identity.user_id:
                raise HTTPException(404, "标签不存在")
            row.name, row.name_key = payload.name, payload.name.casefold()
            db.flush()
            return {"id": row.id, "name": row.name}
    except IntegrityError:
        raise HTTPException(409, "该标签已存在")


@router.delete("/tags/{tag_id}")
def delete_tag(
    tag_id: int, request: Request, identity: Identity = Depends(current_identity)
):
    with request.app.state.factory.begin() as db:
        db.execute(
            delete(UserTag).where(
                UserTag.id == tag_id, UserTag.user_id == identity.user_id
            )
        )
    return {"ok": True}


@router.get("/bookmarks/ids")
def bookmark_ids(request: Request, identity: Identity = Depends(current_identity)):
    with request.app.state.factory() as db:
        return list(
            db.scalars(
                select(Bookmark.news_id).where(Bookmark.user_id == identity.user_id)
            )
        )


@router.get("/bookmarks")
def list_bookmarks(
    request: Request,
    q: str = Query("", max_length=100),
    tag_id: int | None = None,
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=50),
    identity: Identity = Depends(current_identity),
):
    query = select(Bookmark).where(Bookmark.user_id == identity.user_id)
    if q.strip():
        query = query.where(search_condition(Bookmark.snapshot, q.strip()))
    if tag_id:
        query = query.join(BookmarkTag).where(BookmarkTag.tag_id == tag_id)
    with request.app.state.factory() as db:
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.scalars(
            query.order_by(Bookmark.created_at.desc(), Bookmark.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return {
            "items": [bookmark_dict(db, r) for r in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get("/bookmarks/{news_id}")
def get_bookmark(
    news_id: int, request: Request, identity: Identity = Depends(current_identity)
):
    with request.app.state.factory() as db:
        row = db.scalar(
            select(Bookmark).where(
                Bookmark.news_id == news_id, Bookmark.user_id == identity.user_id
            )
        )
        if not row:
            raise HTTPException(404, "收藏不存在")
        return bookmark_dict(db, row)


@router.put("/bookmarks/{news_id}")
def save_bookmark(
    news_id: int,
    payload: BookmarkInput,
    request: Request,
    identity: Identity = Depends(current_identity),
):
    with request.app.state.factory.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        row = db.scalar(
            select(Bookmark).where(
                Bookmark.news_id == news_id, Bookmark.user_id == identity.user_id
            )
        )
        if not row:
            if (
                db.scalar(
                    select(func.count())
                    .select_from(Bookmark)
                    .where(Bookmark.user_id == identity.user_id)
                )
                >= 5000
            ):
                raise HTTPException(409, "收藏已达 5000 条上限")
            query = (
                select(ReportItem)
                .join(DailyReport)
                .where(ReportItem.news_id == news_id)
            )
            if payload.report_date:
                query = query.where(DailyReport.report_date == payload.report_date)
            item = db.scalar(query.order_by(DailyReport.report_date.desc()).limit(1))
            if not item:
                raise HTTPException(404, "该新闻未收录在指定日报中")
            row = Bookmark(
                user_id=identity.user_id, news_id=news_id, snapshot=item.snapshot
            )
            db.add(row)
            db.flush()
        if payload.tag_ids is not None:
            ids = set(payload.tag_ids)
            owned = set(
                db.scalars(
                    select(UserTag.id).where(
                        UserTag.user_id == identity.user_id, UserTag.id.in_(ids)
                    )
                )
            )
            if ids != owned:
                raise HTTPException(404, "标签不存在")
            db.execute(delete(BookmarkTag).where(BookmarkTag.bookmark_id == row.id))
            db.add_all(BookmarkTag(bookmark_id=row.id, tag_id=t) for t in ids)
            db.flush()
        return bookmark_dict(db, row)


@router.delete("/bookmarks/{news_id}")
def remove_bookmark(
    news_id: int, request: Request, identity: Identity = Depends(current_identity)
):
    with request.app.state.factory.begin() as db:
        db.execute(
            delete(Bookmark).where(
                Bookmark.news_id == news_id, Bookmark.user_id == identity.user_id
            )
        )
    return {"ok": True}
