from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from yahoo.spiders.yahoo_spider import YahooSpider
import csv 

def yahoo_finance(input_file, output_file):
	with open(input_file, 'r') as rfile:
		reader = csv.reader(rfile, delimiter=",")

		sheet = []
		append_sht = sheet.append
		for row in reader:
			append_sht(row)	

	crawler = CrawlerProcess(get_project_settings())
	crawler.crawl(YahooSpider, input_data=sheet[1:], output_file=output_file)
	crawler.start()

if __name__ == '__main__':
	yahoo_finance('YF_input_test.csv', "out.csv")