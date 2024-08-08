from fastapi import FastAPI
from scraper_t1_t2 import compute_t1_t2

app = FastAPI()


@app.post("/scrape_t1_t2")
async def run_scrape():
    try:
        await compute_t1_t2()
        return {"message": "Scraping task completed"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050)
