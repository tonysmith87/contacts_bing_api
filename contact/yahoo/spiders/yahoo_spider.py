import scrapy
import json

from datetime import datetime
from pytz import timezone
from collections import OrderedDict

import time

class YahooSpider(scrapy.Spider):
	name = "yahoo"
	allowed_domains = ["finance.yahoo.com"]
	start_urls = [
		"https://query1.finance.yahoo.com/v10/finance/quoteSummary/XOM?formatted=true&lang=en-US&region=US&modules=assetProfile%2CsecFilings%2CcalendarEvents&corsDomain=finance.yahoo.com"
	]
	
	handle_httpstatus_list = [553, 404, 400, 500]
	
	def __init__(self, input_data, output_file):
		self.input_data = input_data
		
		# initial data
		self.profile_url = ['https://query1.finance.yahoo.com/v10/finance/quoteSummary/', '?formatted=true&lang=en-US&region=US&modules=assetProfile%2CsecFilings%2CcalendarEvents&corsDomain=finance.yahoo.com']
		self.statistics_url = ['https://query2.finance.yahoo.com/v10/finance/quoteSummary/', '?formatted=true&crumb=uNwruvthS4V&lang=en-US&region=US&modules=defaultKeyStatistics%2CfinancialData%2CcalendarEvents&corsDomain=finance.yahoo.com']
		self.search_url = "http://finance.yahoo.com/quote/Street_Ticker/key-statistics?ltr=1"
		
		# output file
		self.out_fp = open(output_file, "wb")
		self.header = ['Duns', 'Street_Ticker', 'Street_Exchange', 'Time Stamp', 'Company',
                       'Street', 'City','State', 'Zip', 'Country', 'Phone', 'Website',
                      'Index Membership','Sector', 'Industry', 'Full Time Employees',
                      'Key Exec Name', 'Key Exec Age', 'Key Exec Title',
                      'Key Exec Pay','Key Exec Exercised', 'Market Cap (intraday)5',
                      'Enterprise Value', 'Date (Enterprise Value)',
                      'Trailing P/E (ttm intraday)', 'Forward P/E',
                      'Date (Forward P/E)', 'PEG Ratio (5 yr expected)1',
                      'Price/Sales (ttm)','Price/Book (mrq)',
                      'Enterprise Value/Revenue (ttm)3',
                      'Enterprise Value/EBITDA (ttm)6', 'Fiscal Year Ends',
                      'Most Recent Quarter (mrq)', 'Profit Margin (ttm)',
                      'Operating Margin (ttm)', 'Return on Assets (ttm)',
                      'Return on Equity (ttm)', 'Revenue (ttm)',
                      'Revenue Per Share (ttm)', 'Qtrly Revenue Growth (yoy)',
                      'Gross Profit (ttm)', 'EBITDA (ttm)6',
                      'Net Income Avl to Common (ttm)', 'Diluted EPS (ttm)',
                      'Qtrly Earnings Growth (yoy)', 'Total Cash (mrq)',
                      'Total Cash Per Share (mrq)', 'Total Debt (mrq)',
                      'Total Debt/Equity (mrq)', 'Current Ratio (mrq)',
                      'Book Value Per Share (mrq)', 'Operating Cash Flow (ttm)',
                      'Levered Free Cash Flow (ttm)', 'Beta', '52-Week Change3',
                      'S&P500 52-Week Change3', '52-Week High',
                      '52-Week Low', '50-Day Moving Average3', '200-Day Moving Average3',
                      'Avg Vol (3 month)3', 'Avg Vol (10 day)3',
                      'Shares Outstanding5', 'Float', '% Held by Insiders1',
                      '% Held by Institutions1', 'Shares Short', 'Short Ratio','Short % of Float',
                      'Shares Short (prior month)3', 'Forward Annual Dividend Rate4', 'Forward Annual Dividend Yield4',
                      'Trailing Annual Dividend Yield3', 'Trailing Annual Dividend Yield3',
                      '5 Year Average Dividend Yield4', 'Payout Ratio4', 'Dividend Date3',
                      'Ex-Dividend Date4', 'Last Split Factor (new per old)2',
                      'Last Split Date3']
		self.out_fp.write(','.join(self.header)+"\n")
		
	def start_requests(self):
		for item in self.input_data:
		
			# if input item is invalid, skip this item
			if len(item) < 2:
				continue
			
			# make a request to parse profile information.
			url = self.profile_url[0] + item[1] + self.profile_url[1]
			request = scrapy.Request(url, callback=self.parse_profile)
			request.meta['item'] = item
			yield request
			
	# parse profile information and make a request for parse statistics data
	def parse_profile(self, response):
		# site error handling
		if response.status in [553, 400, 404, 500]:
			return 
	
		yahoo_finance = dict()
		item = response.meta['item']
		
		# put input data into output data
		yahoo_finance['Duns'] = item[0]
		yahoo_finance['Street_Ticker'] = item[1]
		
		try:
			yahoo_finance['Street_Exchange'] = item[2]
		except:
			yahoo_finance['Street_Exchange'] = "N/A"

		# get time stamp
		tz = timezone('EST')
		datetime.now(tz) 
		yahoo_finance["Time Stamp"] = datetime.now(tz).strftime("%a, %b %d, %Y, %I:%M%p") + " EDT"
		
		data = json.loads(response.body)

		if data['quoteSummary']['result'] == None:
			return
		tp_profile = data['quoteSummary']['result'][0]['assetProfile']
		
		# get company profile
		yahoo_finance['Street'] = self.check_value(tp_profile, 'address1')
		
		keys = ['City', 'State', 'Zip', 'Country', 'Phone', 'Website', 'Sector', 'Industry']
		for attr in keys:
			yahoo_finance[attr] = self.check_value(tp_profile, attr.lower())
		yahoo_finance['Full Time Employees'] = self.check_value(tp_profile, 'fullTimeEmployees')
		
		# get company offers
		offers = tp_profile['companyOfficers']
		tp_offers = []
		for offer in offers:
			tp_offer = []
			tp_offer.append(self.check_value(offer, 'name'))
			tp_offer.append(self.check_value(offer, 'age'))
			tp_offer.append(self.check_value(offer, 'title'))
			try:
				tp_offer.append(self.check_value(offer['totalPay'], 'fmt'))
			except:
				tp_offer.append("N/A")

			try:
				tp_offer.append(self.check_value(offer['exercisedValue'], 'fmt'))
			except:
				tp_offer.append("N/A")
			
			tp_offers.append(tp_offer)
			
		yahoo_finance['offers'] = tp_offers
					
		# make a request for parse statistics data
		url = self.search_url.replace("Street_Ticker", yahoo_finance['Street_Ticker'])
		request = scrapy.Request(url, callback=self.parse_statistics)
		request.meta['yahoo_finance'] = yahoo_finance
		request.meta['item'] = response.meta['item']
		yield request
	
	# parse statistics data and save all data into csv file
	def parse_statistics(self, response):
		# site error handling
		if response.status in [553, 400, 404, 500]:
			# make a request to parse profile information.
			request = scrapy.Request(response.url, callback=self.parse_profile)
			request.meta['item'] = response.meta['item']
			yield request
			return
	
		yahoo_finance = response.meta['yahoo_finance']
		yahoo_finance['statistics'] = dict()
		
		statistics = OrderedDict()
			
		yahoo_finance['Company'] = self.validate(response.xpath("//div[@id='quote-header-info']//h6/text()"))
		yahoo_finance['en_date'] = self.validate(response.xpath("//div[@id='quote-header-info']//p[1]//span[4]//span[2]/text()")).split(",")[0]
		
		try:
			detail_statistices = response.body.split("root.App.main =")[1]
			detail_statistices = detail_statistices.split('\n')[0]
			detail_statistices = json.loads(detail_statistices[:-1])
		
			tp_detail = detail_statistices['context']['dispatcher']['stores']['QuoteSummaryStore']
			
			for key in tp_detail['price'].keys():
				yahoo_finance['statistics'][key] = tp_detail['price'][key]
			for key in tp_detail['summaryDetail'].keys():
				yahoo_finance['statistics'][key] = tp_detail['summaryDetail'][key]
				
		except:
			pass
			
		# make a request for parse statistics data
		url = self.statistics_url[0] + yahoo_finance['Street_Ticker'] + self.statistics_url[1]
		request = scrapy.Request(url, callback=self.parse_detail_statistics)
		request.meta['yahoo_finance'] = yahoo_finance
		request.meta['item'] = response.meta['item']
		yield request
			
	# parse statistics data and save all data into csv file
	def parse_detail_statistics(self, response):
		# site error handling
		if response.status in [553, 400, 404, 500]:
			return
	
		yahoo_finance = response.meta['yahoo_finance']
		data = json.loads(response.body)

		try:
			tagert = data['quoteSummary']['result'][0]
			for key in tagert['defaultKeyStatistics'].keys():
				if key == "priceToSalesTrailing12Months":
					continue
				else:
					yahoo_finance['statistics'][key] = tagert['defaultKeyStatistics'][key]
			for key in tagert['financialData'].keys():
				yahoo_finance['statistics'][key] = tagert['financialData'][key]
			for key in tagert['calendarEvents'].keys():
				if key == "earnings":
					for sub_key in tagert['calendarEvents']['earnings'].keys():
						yahoo_finance['statistics'][sub_key] = tagert['calendarEvents']['earnings'][sub_key]
				else:
					yahoo_finance['statistics'][key] = tagert['calendarEvents'][key]
			
		except:
			pass
		
		self.save_data_csv(yahoo_finance)
		
	# save data in csv file
	def save_data_csv(self, data):
		prefix = []
		for key in self.header[:16]:
			prefix.append(self.remove_char(data, key))
		prefix = ','.join(prefix)
			
		statistics_keys = ['marketCap', 'enterpriseValue', 'start_date', 'trailingEps', 'forwardPE', 'end_date', 'pegRatio',\
								'priceToSalesTrailing12Months', 'priceToBook', 'enterpriseToRevenue', 'enterpriseToEbitda', 'lastFiscalYearEnd', 'mostRecentQuarter', \
								'profitMargins', 'operatingMargins', 'returnOnAssets', 'returnOnEquity', 'totalRevenue', 'revenuePerShare', 'revenueGrowth', \
								'grossProfits', 'ebitda' , 'netIncomeToCommon' ,'trailingEps', 'earningsQuarterlyGrowth', 'totalCash', 'totalCashPerShare', \
								'totalDebt', 'debtToEquity', 'currentRatio', 'bookValue', 'operatingCashflow', 'freeCashflow', 'beta', '52WeekChange', \
								'SandP52WeekChange', 'fiftyTwoWeekHigh', 'fiftyTwoWeekLow', 'fiftyDayAverage', 'twoHundredDayAverage', 'averageVolume', \
								'averageDailyVolume10Day', 'sharesOutstanding', 'floatShares', 'heldPercentInsiders', 'heldPercentInstitutions', 'sharesShort', \
								'shortRatio', 'shortPercentOfFloat', 'sharesShortPriorMonth', 'dividendRate', 'dividendYield', 'trailingAnnualDividendRate', \
								'trailingAnnualDividendYield', 'fiveYearAvgDividendYield', 'payoutRatio', 'dividendDate', 'exDividendDate', 'lastSplitFactor',\
								'lastSplitDate']
			
		suffix = []
		for key in statistics_keys:
			if key == 'start_date':
				if len(data['statistics']['earningsDate']) > 0:
					temp = self.remove_char(data['statistics']['earningsDate'][0], 'fmt')
				else:
					temp = "N/A"
			elif key == 'end_date':
				try:
					temp = self.remove_char(data['statistics']['earningsDate'][1], 'fmt')
				except:
					if len(data['statistics']['earningsDate']) > 0:
						temp = self.remove_char(data['statistics']['earningsDate'][0], 'fmt')
					else:
						temp = "N/A"
			elif key == "lastSplitFactor":
				temp = self.remove_char(data['statistics'], key)
			else:
				try:
					temp = self.remove_char(data['statistics'][key], 'fmt')
				except:
					temp = "N/A"
				
				
				
			suffix.append(temp)
			
		suffix = ','.join(suffix)
		
		for offer in data['offers']:
			offer = [self.remove_char(item) for item in offer]
			line = "%s,%s,%s\n" % (prefix, ','.join(offer), suffix)
			
			self.out_fp.write(line.encode("utf8"))
		pass
	
	# check if a key is in dictionary
	def check_value(self, dict, key):
		try:
			value = dict[key]
			if value == None:
				return "0"
			return value
		except:
			return "N/A"
			
	# validate the value of html node
	#	return string value, if data is validated
	#	return "", otherwise
	def validate(self, node):
		if len(node) > 0:
			temp = node[0].extract().strip().encode("utf8")
			return temp
		else:	
			return "N/A"
			
	def remove_char(self, dict, key=""):

		try:
			if key == "":
				try:
					value = str(dict)
				except:
					value = dict
			elif key in dict:
				value = str(dict[key])
			
			else:
				value = "N/A"
		except:
			value = "N/A"
		
		value = value.replace(",", " ")
		value = value.replace("\"", " ")
		return "\"" + value + "\""
