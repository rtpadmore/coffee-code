import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import guam_procurement_mcp.server as server


SAMPLE_HTML = """
<html>
  <body>
    <a href="/wp-gsa-content/uploads/2026/02/GSA-004-26-Amendment-1-Signed.pdf">
      GSA-004-26 AMENDMENT #1 02-11-2026
    </a>
    <a href="https://gsa.doa.guam.gov/wp-gsa-content/uploads/2026/02/GSA-004-26-Amendment-1-Signed.pdf">
      GSA-004-26 AMENDMENT #1 DUPLICATE
    </a>
    <a href="/wp-gsa-content/uploads/2026/04/GSA-007-26-NOTICE-TO-ALL-PROSPECTIVE-BIDDERS-CANCELLED-04-21-2026.pdf">
      GSA-007-26 NOTICE TO ALL PROSPECTIVE BIDDERS "CANCELLED" 04-21-2026
    </a>
    <a href="/wp-gsa-content/uploads/2024/01/Invitation-for-Bid-No.-GSA-001-24-2.pdf">
      GSA-001-24 COMMERCIAL OFFICE SPACE LEASE FOR GUAM PUBLIC ASSISTANCE
    </a>
    <a href="/wp-gsa-content/uploads/2023/04/Signed-bid-contract-GSA-011-23.pdf">
      GSA-011-23 SIGNED BID CONTRACT
    </a>
    <a href="/wp-gsa-content/uploads/2026/05/GSA-024-26-BID-STATUS.pdf">
      GSA-024-26 BID STATUS
    </a>
    <a href="/wp-gsa-content/uploads/2026/03/RFP-001-26-REQUEST-FOR-PROPOSAL.pdf">
      RFP-001-26 REQUEST FOR PROPOSAL
    </a>
    <a href="/wp-gsa-content/uploads/2026/03/GSA-010-26-Questions-and-Responses.pdf">
      GSA-010-26 QUESTIONS AND RESPONSES
    </a>
    <a href="/wp-gsa-content/uploads/2026/03/GSA-012-26-INTENT-TO-AWARD.pdf">
      GSA-012-26 INTENT TO AWARD
    </a>
    <a href="/wp-gsa-content/uploads/2026/03/GSA-013-26-STAY-OF-PROCUREMENT.pdf">
      GSA-013-26 STAY OF PROCUREMENT
    </a>
    <a href="/about/">About GSA</a>
  </body>
</html>
"""


class MetadataExtractionTests(unittest.TestCase):
    def test_document_year_uses_explicit_year_and_solicitation_fallback(self):
        self.assertEqual(
            server.document_year("GSA-004-26 AMENDMENT #1 02-11-2026", ""),
            2026,
        )
        self.assertEqual(
            server.document_year(
                "GSA-024-26 BID STATUS",
                "https://example.test/GSA-024-26-BID-STATUS.pdf",
            ),
            2026,
        )
        self.assertEqual(
            server.document_year(
                "Signed Contract",
                "https://example.test/wp-gsa-content/uploads/2024/contract.pdf",
            ),
            2024,
        )

    def test_document_kind_classification(self):
        cases = {
            "GSA-001-24 INVITATION FOR BID": "ifb",
            "RFP-001-26 REQUEST FOR PROPOSAL": "rfp",
            "GSA-004-26 AMENDMENT #1": "amendment",
            "GSA-012-26 INTENT TO AWARD": "award",
            "GSA-024-26 BID STATUS": "bid_status",
            "GSA-007-26 CANCELLED": "cancellation",
            "GSA-011-23 SIGNED BID CONTRACT": "contract",
            "GSA-010-26 QUESTIONS AND RESPONSES": "questions_and_responses",
            "GSA-013-26 STAY OF PROCUREMENT": "stay_of_procurement",
        }

        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(server.document_kind(title), expected)

    def test_solicitation_number_is_normalized(self):
        self.assertEqual(
            server.solicitation_number(
                "Invitation for Bid No. GSA_001 24",
                "https://example.test/document.pdf",
            ),
            "GSA-001-24",
        )
        self.assertEqual(
            server.solicitation_number(
                "REQUEST FOR PROPOSAL",
                "https://example.test/RFP-001-26.pdf",
            ),
            "RFP-001-26",
        )


class RecordParsingTests(unittest.TestCase):
    def test_parse_filters_query_year_and_deduplicates_urls(self):
        records = server.parse_procurement_records(
            SAMPLE_HTML,
            query="amendment",
            year=2026,
            max_results=10,
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "GSA-004-26 AMENDMENT #1 02-11-2026")
        self.assertEqual(records[0]["kind"], "amendment")
        self.assertEqual(records[0]["year"], 2026)
        self.assertEqual(records[0]["solicitation_number"], "GSA-004-26")
        self.assertEqual(records[0]["source"], server.GSA_SOURCE_NAME)
        self.assertEqual(records[0]["source_url"], server.GSA_IFB_URL)

    def test_parse_returns_planned_metadata_fields(self):
        records = server.parse_procurement_records(
            SAMPLE_HTML,
            query="office space",
            year=2024,
            max_results=10,
        )

        self.assertEqual(
            records,
            [
                {
                    "title": "GSA-001-24 COMMERCIAL OFFICE SPACE LEASE FOR GUAM PUBLIC ASSISTANCE",
                    "url": "https://gsa.doa.guam.gov/wp-gsa-content/uploads/2024/01/Invitation-for-Bid-No.-GSA-001-24-2.pdf",
                    "kind": "ifb",
                    "year": 2024,
                    "solicitation_number": "GSA-001-24",
                    "source": server.GSA_SOURCE_NAME,
                    "source_url": server.GSA_IFB_URL,
                }
            ],
        )


class ToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_search_procurement_documents_uses_mocked_fetch(self):
        with patch.object(
            server,
            "fetch_gsa_ifb_html",
            new=AsyncMock(return_value=SAMPLE_HTML),
        ):
            payload = json.loads(
                await server.search_procurement_documents(
                    "cancelled",
                    year=2026,
                    max_results=5,
                )
            )

        self.assertEqual(payload["source"], server.GSA_SOURCE_NAME)
        self.assertEqual(payload["source_url"], server.GSA_IFB_URL)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["kind"], "cancellation")
        self.assertEqual(payload["results"][0]["solicitation_number"], "GSA-007-26")
        self.assertIn("PDF body text is not searched", payload["limitations"][1])

    async def test_search_procurement_documents_clamps_max_results(self):
        html = "\n".join(
            f'<a href="/wp-gsa-content/uploads/2026/01/GSA-{i:03d}-26.pdf">'
            f"GSA-{i:03d}-26 INVITATION FOR BID</a>"
            for i in range(1, 61)
        )

        with patch.object(
            server,
            "fetch_gsa_ifb_html",
            new=AsyncMock(return_value=html),
        ):
            high_payload = json.loads(
                await server.search_procurement_documents("", max_results=100)
            )
            low_payload = json.loads(
                await server.search_procurement_documents("", max_results=-5)
            )

        self.assertEqual(high_payload["count"], 50)
        self.assertEqual(low_payload["count"], 1)


if __name__ == "__main__":
    unittest.main()
