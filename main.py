from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from scraper import scrape_judgments
from g_drive import initiate_google_auth_flow, exchange_code_for_service, upload_pdf
from models import uploaded_judgements, SessionLocal
import requests

app = FastAPI()

@app.get("/authorize")
def authorize():
    auth_url, state = initiate_google_auth_flow()
    return RedirectResponse(auth_url)

@app.get("/oauth2callback")
def oauth2callback(request: Request):
    params = request.query_params
    if "error" in params:
        raise HTTPException(status_code=400, detail=params["error"])
    service = exchange_code_for_service(params["state"], params["code"])
    judgments = scrape_judgments(service)

    db = SessionLocal()
    uploaded = []
    for j in judgments:
        pdf = requests.get(j["link"])
        pdf.raise_for_status()
        try:
            file_id = upload_pdf(service, pdf.content, f"{j['unique_id']}.pdf")
            entry = uploaded_judgements(
                id=j["unique_id"], matter_no=j["matter"],
                order_date=j["date"], drive_file_id=file_id
            )
            db.add(entry)
            db.commit()
            uploaded.append({
                "matter": j["matter"],
                "coram": j["coram"],
                "date": j["date"],
                "drive_file_id": file_id
            })
        except Exception as ex:
            # skip failed uploads
            continue
    db.close()
    return {"uploaded": uploaded}

@app.get("/login-and-upload")
def login_and_upload():
    return RedirectResponse("/authorize")
