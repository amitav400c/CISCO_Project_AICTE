"""
NetSage AI - Human Review & Responsible AI Logger
Manages human expert review of AI diagnoses (Accepted, Edited, Rejected),
persistence in SQLite, and generates the Responsible AI Log.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional

class HumanReviewManager:
    def __init__(self, db_path: Optional[Path] = None):
        root = Path(__file__).resolve().parent.parent
        self.db_path = db_path or (root / "data" / "netsage.db")

    def log_diagnosis(self, case_id: str, diag_data: Dict[str, Any]) -> int:
        """Stores an AI diagnosis into the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO diagnoses (
                case_id, ai_root_cause, ai_confidence, ai_confidence_level,
                ai_evidence, ai_next_command, ai_fix_steps, ai_osi_layer,
                ai_fault_type, review_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (
            case_id,
            diag_data.get("root_cause", ""),
            diag_data.get("confidence", 0.0),
            diag_data.get("confidence_level", "Medium"),
            "\n".join(diag_data.get("evidence", [])),
            diag_data.get("next_command", ""),
            "\n".join(diag_data.get("fix_steps", [])),
            diag_data.get("osi_layer", ""),
            diag_data.get("fault_type", "")
        ))

        diag_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return diag_id

    def submit_review(self, diag_id: int, status: str, corrected_cause: str = "", corrected_fix: str = "", notes: str = ""):
        """
        Submits human review verdict: 'Accepted', 'Edited', or 'Rejected'.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE diagnoses
            SET review_status = ?,
                human_corrected_root_cause = ?,
                human_corrected_fix = ?,
                human_notes = ?,
                reviewed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, corrected_cause, corrected_fix, notes, diag_id))

        conn.commit()
        conn.close()

    def get_all_reviews(self) -> List[Dict[str, Any]]:
        """Returns all diagnoses and their review status."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT d.*, c.symptom, c.lab_source, c.expected_fault
            FROM diagnoses d
            LEFT JOIN cases c ON d.case_id = c.case_id
            ORDER BY d.id DESC
        """)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_review_metrics(self) -> Dict[str, Any]:
        """Calculates agreement rates and status counts."""
        reviews = self.get_all_reviews()
        total = len(reviews)
        if total == 0:
            return {"total": 0, "accepted": 0, "edited": 0, "rejected": 0, "pending": 0, "agreement_rate": 0.0}

        accepted = sum(1 for r in reviews if r.get("review_status") == "Accepted")
        edited = sum(1 for r in reviews if r.get("review_status") == "Edited")
        rejected = sum(1 for r in reviews if r.get("review_status") == "Rejected")
        pending = sum(1 for r in reviews if r.get("review_status") == "Pending")

        reviewed_total = accepted + edited + rejected
        agreement_rate = (accepted / reviewed_total * 100) if reviewed_total > 0 else 0.0

        return {
            "total": total,
            "accepted": accepted,
            "edited": edited,
            "rejected": rejected,
            "pending": pending,
            "agreement_rate": round(agreement_rate, 1)
        }

if __name__ == "__main__":
    mgr = HumanReviewManager()
    print("Review metrics:", mgr.get_review_metrics())
