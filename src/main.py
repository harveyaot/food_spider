import uvicorn
from search_engine.api import app
from fastapi.staticfiles import StaticFiles

# Mount the static files
app.mount(
    "/", StaticFiles(directory="src/search_engine/static", html=True), name="static"
)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8001)
