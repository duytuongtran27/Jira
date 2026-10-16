import re
from datetime import datetime

class DateVerify:
    SINGLE_MONTH_PATTERN = r'^\d{1,2}/\d{4}$'
    MULTIPLE_MONTHS_PATTERN = r'^\d{1,2}/\d{4}-\d{1,2}/\d{4}$'

    def __init__(self) -> None:
        pass

    @classmethod
    def validate(cls, date_string):
        """
        Validates if the input follows one of the accepted formats.

        Args:
            date_string (str): The date string to validate

        Returns:
            bool: True if format is valid, False otherwise
        """
        if not isinstance(date_string, str):
            return False

        date_string = date_string.strip()

        # Check for single month format (m/y)
        if re.match(cls.SINGLE_MONTH_PATTERN, date_string):
            return cls._validate_single_month(date_string)

        # Check for multiple months format (m1/y1-m2/y2)
        elif re.match(cls.MULTIPLE_MONTHS_PATTERN, date_string):
            return cls._validate_multiple_months(date_string)

        return False

    @staticmethod
    def _validate_single_month(date_string):
        """Validates single month format and checks if month is valid (1-12)."""
        try:
            month, year = date_string.split('/')
            month = int(month)
            year = int(year)

            # Check valid month range
            if 1 <= month <= 12 and year > 0:
                return True
            return False
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _validate_multiple_months(date_string):
        """Validates multiple months format and checks if dates are valid."""
        try:
            start_date, end_date = date_string.split('-')

            # Parse start date (m1/y1)
            m1, y1 = start_date.split('/')
            # Parse end date (m2/y2)
            m2, y2 = end_date.split('/')

            # Convert to integers
            m1, y1, m2, y2 = int(m1), int(y1), int(m2), int(y2)

            # Validate month ranges (1-12) and year is positive
            if not (1 <= m1 <= 12 and 1 <= m2 <= 12 and y1 > 0 and y2 > 0):
                return False

            # Ensure start date is before or equal to end date
            if (y1 > y2) or (y1 == y2 and m1 > m2):
                return False

            return True
        except (ValueError, AttributeError):
            return False

class UserInputDateVerify:

    @staticmethod
    def verify_single_month_selection(selected_month,selected_year):
        verified_date = {
            'start_m': selected_month,
            'start_y': selected_year,
            'end_m': selected_month,
            'end_y': selected_year
        }
        if selected_month == 1:
            verified_date['start_m'] = 12
            verified_date['start_y'] = selected_year - 1
            verified_date['end_m'] = 1
            verified_date['end_y'] = selected_year
        else:
            verified_date['start_m'] = selected_month - 1
            verified_date['start_y'] = selected_year
        return verified_date