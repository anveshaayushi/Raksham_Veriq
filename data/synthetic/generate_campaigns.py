"""veriq/data/synthetic/generate_campaigns.py

SYNTHETIC campaign data (Claude A, 24 Oct): fictional firms and UPI IDs grouped into two "campaigns", plus the registry
records those campaigns would create. No randomness: the output is fully determined by CAMPAIGNS below, so running it
twice gives byte-identical files (tests/completeness/test_bench_smoke.py checks this against the committed files).

    python data/synthetic/generate_campaigns.py      -> data/synthetic/campaign_cases.json, registry_seed.json
"""
import json
from pathlib import Path

CAMPAIGNS = [
    {
        "campaign_id": "CAMP-01-SEBI-IMPERSONATION",
        "claimed_firm": "Navyug Wealth Research",
        "mules": ["ramesh.k@upi", "sunita.t@upi"],
        "num_victims": 8,
        "is_fraud": True,
    },
    {
        "campaign_id": "CAMP-02-TASK-FRAUD",
        "claimed_firm": "Global Media Task Pro",
        "mules": ["pay.task99@okhdfcbank"],
        "num_victims": 10,
        "is_fraud": True,
    }
]

def generate_campaign_data(out_dir: str = "data/synthetic") -> None:
    p = Path(out_dir)
    p.mkdir(parents=True, exist_ok=True)
    cases = []
    registry_records = []

    for camp in CAMPAIGNS:
        for v_idx in range(1, camp["num_victims"] + 1):
            cases.append({
                "case_id": f"{camp['campaign_id']}-V{v_idx:02d}",
                "claimed_firm": camp["claimed_firm"],
                "payee": camp["mules"][v_idx % len(camp["mules"])],
                "is_fraud": camp["is_fraud"]
            })
        if camp["is_fraud"]:
            for mule in camp["mules"]:
                registry_records.append({
                    "payee_id": mule,
                    "status": "linked",
                    "independent_reporters": camp["num_victims"],
                    "reviewer_confirmed": True,
                    "source": "SYNTHETIC campaign seed (fictional; not any real registry)",
                    "note": f"Reported across {camp['campaign_id']}"
                })

    with open(p / "campaign_cases.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(cases, f, indent=2)
    with open(p / "registry_seed.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(registry_records, f, indent=2)

if __name__ == "__main__":
    generate_campaign_data()
    print("Synthetic campaign data generated.")
