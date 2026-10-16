import pytz

class ConvertLib: 

    @staticmethod
    def convert_milliseconds_to_hours(milliseconds):
        if milliseconds is not None:
            return (milliseconds / 1000.0) / 3600.0
        return 0

    @staticmethod
    def convert_to_GMT7(date):
        if date is None:
            return None
        if date.tzinfo is None:
            date = date.replace(tzinfo=pytz.UTC)
        vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        return date.astimezone(vietnam_tz) 