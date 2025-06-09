class ScrapingReportGenerator:
    def __init__(self, scraping_report):
        self.scraping_report = scraping_report

    def generate(self):
        report = {
            "total_scraped": self.scraping_report.total_scraped,
            "total_failed": self.scraping_report.total_failed,
            "scraped_items": self.scraping_report.scraped_items,
            "failed_items": self.scraping_report.failed_items,
        }
        return report