from datetime import datetime

def timestamp_to_datetime(timestamp: int, type: str, output_format: str) -> datetime:
    if type == "seconds":
        return datetime.fromtimestamp(timestamp).strftime(output_format)
    elif type == "milliseconds":
        return datetime.fromtimestamp(timestamp / 1000).strftime(output_format)
    
def datetime_to_timestamp(date: datetime, type: str) -> int:
    if type == "seconds":
        return int(date.timestamp())
    elif type == "milliseconds":
        return int(date.timestamp() * 1000)