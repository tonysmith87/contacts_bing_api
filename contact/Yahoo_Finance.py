from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from yahoo.spiders.yahoo_spider import YahooSpider
import csv 
import sys

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
	
	input_file = sys.argv[1]
	output_file = sys.argv[2]
	yahoo_finance(input_file, output_file)
