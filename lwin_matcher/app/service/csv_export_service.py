from __future__ import annotations
import csv
import io
from typing import Any
from flask import Response

class CsvExportService:
    @staticmethod
    def to_response(
        data: list[dict[str, Any]],
        filename: str = "export.csv",
    ) -> Response:
        output = io.StringIO()
        writer = csv.writer(output)

        if data:
            writer.writerow(data[0].keys())
            for row in data:
                writer.writerow(row.values())
        else:
            writer.writerow(["No Data"])

        csv_bytes = output.getvalue().encode("utf-8-sig")
        output.close()

        response = Response(csv_bytes, mimetype="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response