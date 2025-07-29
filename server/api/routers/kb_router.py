# server/api/routers/kb_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID

from database import KnowledgeBaseArticle, get_async_session

router = APIRouter()

# -----------------------------------------------------------
# Knowledge Base Article Management
# These endpoints are now in their own router.
# For a production system, these would typically be behind agent authentication.
# For this demo, we'll keep them public for ease of use.
# -----------------------------------------------------------
@router.post("/kb/articles", status_code=status.HTTP_201_CREATED)
async def create_kb_article(
    title: str = Form(...),
    content: str = Form(...),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create KB article.
    """
    article = KnowledgeBaseArticle(title=title, content=content, tags=tags)
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return {"message": "Knowledge base article created successfully", "article_id": str(article.id)}

@router.get("/kb/articles", response_model=List[dict])
async def get_kb_articles(
    db: AsyncSession = Depends(get_async_session)
):
    """
    List KB articles.
    """
    result = await db.execute(select(KnowledgeBaseArticle).order_by(KnowledgeBaseArticle.title))
    articles = result.scalars().all()
    return [{"id": str(a.id), "title": a.title, "content": a.content, "tags": a.tags, "last_updated": a.last_updated.isoformat()} for a in articles]

@router.delete("/kb/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete KB article by ID.
    """
    result = await db.execute(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.id == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    
    await db.delete(article)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)