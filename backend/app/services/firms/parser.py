import csv
from io import StringIO
from typing import List, Dict, Any

class FirmsParser:
    def parse_csv(self, csv_data: str) -> List[Dict[str, Any]]:
        """
        Parses FIRMS CSV data into a list of dictionaries.
        """
        if not csv_data or not csv_data.strip():
            return []
            
        f = StringIO(csv_data.strip())
        reader = csv.DictReader(f)
        records = [row for row in reader]
        return records
