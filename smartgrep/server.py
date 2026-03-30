from fastapi import FastAPI
from pydantic import BaseModel
from smartgrep.searcher import CodeSearcher

app = FastAPI()
searcher = CodeSearcher()

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    threshold: float = 1.3
    hybrid: bool = True
    max_rerank: int = 50

@app.post("/search")
def search(request: SearchRequest):
    results = searcher.search(
        query=request.query,
        limit=request.limit,
        threshold=request.threshold,
        hybrid=request.hybrid,
        max_rerank=request.max_rerank
    )
    return {"results": results}
