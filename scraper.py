import requests
import json
from bs4 import BeautifulSoup
from models import uploaded_judgements, SessionLocal
from g_drive import file_exists_on_drive, upload_pdf

BASE_URL = "https://bombayhighcourt.nic.in/recentorderjudgment.php"

with open("config.json", "r") as f:
    config = json.load(f)

JUDGE_BENCHES = config["benches"]

def normalize(text: str) -> str:
    return " ".join(text.strip().split())

def scrape_judgments(service):
    resp = requests.get(BASE_URL)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    rows = soup.select("table tr")[1:]
    results = []
    db = SessionLocal()

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        matter = normalize(cols[1].text)
        party = normalize(cols[2].text)
        coram = normalize(cols[3].text)
        date = normalize(cols[4].text)

        # Match exact bench
        for bench in JUDGE_BENCHES:
            if all(judge in coram for judge in bench):
                break
        else:
            continue

        unique_id = f"{matter}_{party}_{coram}_{date}".replace("/", "_")
        record = db.query(uploaded_judgements).filter_by(id=unique_id).first()
        drive_file_id = None

        # Check deduplication + Drive file existence
        if record:
            if file_exists_on_drive(service, record.drive_file_id):
                continue
            else:
                db.delete(record)
                db.commit()

        link_tag = cols[1].find("a")
        if not link_tag or "href" not in link_tag.attrs:
            continue
        link = "https://bombayhighcourt.nic.in/" + link_tag["href"]

        pdf_resp = requests.get(link)
        if pdf_resp.ok:
            filename = f"{unique_id}.pdf"
            drive_file_id = upload_pdf(service, pdf_resp.content, filename)

            db.add(uploaded_judgements(
                id=unique_id,
                matter_no=matter,
                order_date=date,
                drive_file_id=drive_file_id
            ))
            db.commit()

        results.append({
            "matter": matter,
            "party": party,
            "coram": coram,
            "date": date,
            "link": link,
            "google_drive_file_id": drive_file_id
        })

    db.close()
    return results
