from datetime import datetime, timedelta

class IntervalCalculator:
    @staticmethod
    def calc_interval_average(dts):
        if len(dts) < 2:
            return None
        sorted_dts = sorted(dts)
        intervals = [
            (curr - prev).total_seconds() / 86400
            for prev, curr in zip(sorted_dts, sorted_dts[1:])
            if curr >= prev
        ]
        return sum(intervals) / len(intervals) if intervals else None

    @classmethod
    def calculate_averages(cls, date_values):
        if len(date_values) < 2:
            return (None, None, None, None)

        date_values.sort(reverse=True)
        recent_gap = cls.calc_interval_average(date_values[:2])
        avg_last_10 = cls.calc_interval_average(date_values[:10])

        latest_dt = date_values[0]
        last_30d = [
            dt for dt in date_values
            if latest_dt - timedelta(days=30) <= dt <= latest_dt
        ]
        avg_last_30d = cls.calc_interval_average(last_30d)
        avg_total = cls.calc_interval_average(date_values)

        return (recent_gap, avg_last_10, avg_last_30d, avg_total)