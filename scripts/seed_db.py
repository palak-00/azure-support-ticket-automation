"""
Database Seed Script.
Populates the database with initial training sample tickets for testing and exploration.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, init_db
from app.models.schemas import TicketCreate
from app.services.ticket_service import TicketService


def seed_tickets():
    init_db()
    db = SessionLocal()
    service = TicketService(db)

    dataset_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "tickets_dataset.json"
    )

    with open(dataset_path, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    # Ingest the 20 training tickets
    train_tickets = [t for t in tickets if t["split"] == "train"]
    seeded_count = 0

    print(f"Seeding {len(train_tickets)} training tickets into database...")
    for t in train_tickets:
        try:
            payload = TicketCreate(ticket_id=t["ticket_id"], message=t["message"])
            service.create_ticket(payload)
            seeded_count += 1
        except Exception:
            # Skip if already exists
            pass

    print(f"Successfully seeded {seeded_count} tickets.")
    db.close()


if __name__ == "__main__":
    seed_tickets()
