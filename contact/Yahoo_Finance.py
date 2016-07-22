import requests
import cProfile
import csv
import datetime
import sys
import re
from bs4 import BeautifulSoup




def get_stock_data(soup_ks):
    """Return a dictionary of the Key Statistics data.

    Keyword arguments:
    soup_ks -- BeautifulSoup object from parsed url http://finance.yahoo.com/q/ks?s=SYM
    """
    header = soup_ks.find_all("td", {"class": "yfnc_tablehead1"})
    value = soup_ks.find_all("td", {"class": "yfnc_tabledata1"})

    # Return None if no data for company on profile site.
    if len(value)==0:
        return None

    for i in range(len(header)):
        header[i] = header[i].text.replace(":", "")

    for i in range(len(value)):
        value[i] = value[i].text

    # Get the date from the header where applicable.
    # Except ValueError in case "(" not found.
    for i in (1, 3, 34, 35, 44, 45, 46):
        try:
            paran_indx = header[i].index("(")
            value.append(header[i][paran_indx:])
            header[i]= header[i][0:paran_indx].strip()
        except ValueError:
            pass
        header.append('Date ' + '(' + header[i] + ')')
            #print("i: ", i, " ", header[i])

    company_stock_dict = dict(zip(header, value))

    for k in company_stock_dict:
        try:
            company_stock_dict[k] = float(company_stock_dict[k])
        except:
            pass

    return company_stock_dict

def get_details(soup_pr):
    """Return a dictionary of the Details and Key Execs table data.

       Keyword arguments:
       soup_pr -- BeautifulSoup object from parsed url http://finance.yahoo.com/q/pr?s=SYM
       """
    # Return None if Details table is not found at url (profiles for those like STZ made
    # this necessary)
    try:
        if soup_pr.find("span", {"class":"yfi-module-title"}).text!="Details":
            return None
    except AttributeError:
        return None

    details_header = ['Index Membership', 'Sector', 'Industry', 'Full Time Employees',
                      'Key Execs']
    value = soup_pr.find_all("td", {"class": "yfnc_tabledata1"})

    # Return None if no data for company on profile site.
    if len(value)==0:
        return None

    details_value = []
    append_val = details_value.append
    for i in range(0, 4):
        append_val(value[i].text)

    key_execs_value =[]
    append_exec = key_execs_value.append
    for i in range(4, len(value)):
        append_exec(value[i].text.replace('  ', ''))

    for i in range(len(key_execs_value)):
        # Separates the name from age+title on "\n" chars into an array (tmp_arr)
        # Assumes key_execs
        tmp_arr = key_execs_value[i].splitlines()
        if len(tmp_arr)>1:  #
            tmp_arr[0] = tmp_arr[0].replace(",", "").strip()  # name
            # If age in the exec's title
            if tmp_arr[1][0:2].isdigit():
                tmp_arr.append(tmp_arr[1][2:])  # title
                tmp_arr[1] = tmp_arr[1][0:2]  # age
            # If no age is in exec's title
            else:
                tmp_arr.append(tmp_arr[1].strip())
                tmp_arr[1]=''
        key_execs_value[i] = tmp_arr

    key_execs_arr = []
    while len(key_execs_value)>0:
        tmp_exec_dict = {'Key Exec Exercised': '', 'Key Exec Pay': '', 'Key Exec Name':'',
                         'Key Exec Age': '', 'Key Exec Title': ''}
        tmp_name_age_title_arr = key_execs_value.pop(0)
        tmp_exec_dict['Key Exec Name'] = tmp_name_age_title_arr[0]
        tmp_exec_dict['Key Exec Age'] = tmp_name_age_title_arr[1]
        tmp_exec_dict['Key Exec Title'] = tmp_name_age_title_arr[2]
        tmp_exec_dict['Key Exec Pay'] = key_execs_value.pop(0)[0]
        tmp_exec_dict['Key Exec Exercised'] = key_execs_value.pop(0)[0]

        key_execs_arr.append(tmp_exec_dict)

        # Debugging
        '''print("\nlen(key execs value): ", len(key_execs_value))
        print(key_execs_value)
        print("\nkey_execs_arr: ", key_execs_arr)
        print("\ntmp exec dict: ", tmp_exec_dict)'''

    details_value.append(key_execs_arr)

    company_details_dict = dict(zip(details_header, details_value))
    return company_details_dict


def get_profile(soup):
    """Return a dictionary of the Profile table data.

       Keyword arguments:
       soup_pr -- BeautifulSoup object from parsed url http://finance.yahoo.com/q/pr?s=SYM
       """
    # Return object
    company_profile_dict = {'Street': '', 'City': '', 'State': '', 'Zip': '',
                            'Country': '', 'Phone': '', 'Website': ''}

    rslt_set = soup.find("td", {"class": "yfnc_modtitlew1"})

    try:
        tag = rslt_set.find("br")

        # container for recursoup() parsing results
        rslt_list = []
        if 'Website:' in str(rslt_set):
            base_case = 'Website:'
        else:
            base_case = 'Phone:'
        recur_soup(tag.next_element, rslt_list, base_case)
        #print(len(rslt_list))
    except AttributeError:
        return None
    '''
    and ("Fax:" not in rslt_list[-3] \
    or "Fax:"not in rslt_list[-2] \
    or "Fax:" not in rslt_list[-1]) \
    '''
    if len(rslt_list)>10:
        return None
    #print(rslt_list)
    for i in range(len(rslt_list)):
        try:
            # Street data mapping conditions 1
            if len(rslt_list) > 6 \
              and "\n" not in rslt_list[1] \
              and company_profile_dict['Street'] == '':
                #print("IF 1, ", rslt_list[0], " ", rslt_list[1])
                company_profile_dict['Street'] = rslt_list[0] + ", " + rslt_list[1]
            # City, State, Zip data mapping conditions
            elif '   ' in rslt_list[i]:
                #print("IF 5, ", rslt_list[i])
                cty_st_zip = rslt_list[i].replace('  ', '').splitlines()
                company_profile_dict['City'] = cty_st_zip[0].replace(',', '').strip()
                company_profile_dict['State'] = cty_st_zip[1][0:2]
                company_profile_dict['Zip'] = cty_st_zip[1][3:]
            # Country data mapping conditions
            elif " - " in rslt_list[i]:
                #print("IF 4, ", rslt_list[i])
                company_profile_dict['Country'] = rslt_list[i].replace('-', '').strip()
            # Phone data mapping conditions
            elif 'Phone:' in rslt_list[i]:
                #print("IF 2, ", rslt_list[i])
                company_profile_dict['Phone'] = rslt_list[i].replace('Phone: ', '')
            # Website mapping conditions
            elif '.com' in rslt_list[i]:
                #print("IF 3, ", rslt_list[i])
                company_profile_dict['Website'] = rslt_list[i]
            # Street data mapping conditions 2
            elif company_profile_dict['Street']=='':
                #print("IF 6, ", rslt_list[i])
                company_profile_dict['Street'] = rslt_list[0]
        except IndexError:
            continue

    #print(company_profile_dict)
    return company_profile_dict


def recur_soup(tag, rslt_list, base_case):
    """Recursive helper function for get profile. Return array of tags until either string
    'Phone:' or 'Website:', or until (try/except) no html elements remain.

    Keyword arguments:
    tag -- html tag that is two elements away from the value of tag in each previous
    function call
    rslt_list -- array of tags. Contains the results from running this function
    base_case -- string ('Phone:' or 'Website:'. Remains constant throughout recursive
    process.
    """
    if base_case in tag:
        if base_case=='Phone:':
            #print("base_case = ", base_case,", tag = ", tag)
            rslt_list.append(tag)
            return None
        else:
            #print("base_case, ", tag)
            rslt_list.append(tag.next_element.next_element)
            return None
    else:
        rslt_list.append(tag)
        #print(tag)
        try:
            recur_soup(tag.next_element.next_element, rslt_list, base_case)
        except:
            return



def row_x_num_execs(dictionary):
    """Return a list of dictionaries (one for each key exec)

    Keyword arguments:
    dictionary -- output_dict after updates from 3 workhorse "get" functions

    Except KeyError if "Key Execs" not found in dictionary keys
    """
    try:
        key_execs_dicts_list = dictionary['Key Execs']
        del dictionary['Key Execs']
        #print("\noutput_dict: ", output_dict)
        output_dicts_list = []
        #print("output_dicts_list: ", output_dicts_list)
    except KeyError as e:
        key_execs_dicts_list = []
        output_dicts_list = []
        #print(e)
        pass
    #append_odl_2 = output_dicts_list.append
    for ke_d in key_execs_dicts_list:
            #print("\nke_d: ", ke_d)
            tmp_dictionary = dictionary.copy()
            #print("\ntmp_dictionary: ", tmp_dictionary)
            tmp_dictionary.update(ke_d)
            #append_odl_2(tmp_dictionary)
            output_dicts_list.append(tmp_dictionary)
    #print("odl: ", output_dicts_list)
    return output_dicts_list


def yahoo_finance(input_file, output_file):
    '''
    #TEST CASE
    pp = pprint.PrettyPrinter(indent=4)
    symbol = "WMT"
    url_ks = "http://www.finance.yahoo.com/q/ks?s=" + symbol
    r_ks = requests.get(url_ks)
    soup_ks = BeautifulSoup(r_ks.content, "html.parser")
    #get_stock_data(soup_ks)
    '''
    '''
    #TEST CASE
    symbol = ["VULC", 'AAPL']
    for s in symbol:
        url_pr = "http://www.finance.yahoo.com/q/pr?s=" + s
        r_pr = requests.get(url_pr)
        soup_pr = BeautifulSoup(r_pr.content, "html.parser")
        print(s)
        #print(get_profile(soup_pr))
        print(get_details(soup_pr))
    '''
    # input_file = input('Please enter the name of the csv input file (including ".csv"): ')

    with open(input_file, 'r') as rfile:
        reader = csv.reader(rfile, delimiter=",")

        sheet = []
        append_sht = sheet.append
        for row in reader:
            append_sht(row)

    with open(output_file, 'w') as wfile:

        # Set to False after writing the header once
        write_header_bool = True

        # Not exactly the same keys as the returns from the 3 get methods -
        # includes "Key Exec ___"
        fieldnames = ['Duns', 'Street_Ticker', 'Street_Exchange', 'Time Stamp', 'Company',
                       'Street', 'City','State', 'Zip', 'Country', 'Phone', 'Website',
                      'Index Membership','Sector', 'Industry', 'Full Time Employees',
                      'Key Exec Name', 'Key Exec Age', 'Key Exec Title',
                      'Key Exec Pay','Key Exec Exercised', 'Market Cap (intraday)5',
                      'Enterprise Value', 'Date (Enterprise Value)',
                      'Trailing P/E (ttm, intraday)', 'Forward P/E',
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
                      'Date (52-Week High)', '52-Week Low', 'Date (52-Week Low)',
                      '50-Day Moving Average3', '200-Day Moving Average3',
                      'Avg Vol (3 month)3', 'Avg Vol (10 day)3',
                      'Shares Outstanding5', 'Float', '% Held by Insiders1',
                      '% Held by Institutions1', 'Shares Short','Date (Shares Short)',
                      'Short Ratio','Date (Short Ratio)','Short % of Float',
                      'Date (Short % of Float)','Shares Short (prior month)3',
                      'Forward Annual Dividend Rate4', 'Forward Annual Dividend Yield4',
                      'Trailing Annual Dividend Yield3', 'Trailing Annual Dividend Yield3',
                      '5 Year Average Dividend Yield4', 'Payout Ratio4', 'Dividend Date3',
                      'Ex-Dividend Date4', 'Last Split Factor (new per old)2',
                      'Last Split Date3']

        get = requests.get
        for i in range(1, len(sheet)):
            #if i>1:
                #break

            symbol = sheet[i][1]
            #print(symbol)


            # Testing individual symbols
            #symbol = "Gpea"


            # Use ks url for soup for key stats function
            url_ks = "http://www.finance.yahoo.com/q/ks?s={}".format(symbol)
            r_ks = get(url_ks)
            soup_ks = BeautifulSoup(r_ks.content, "html.parser")

            # Use pr url for soup for profile & details functions
            url_pr = "http://www.finance.yahoo.com/q/pr?s={}".format(symbol)
            r_pr = get(url_pr)
            soup_pr = BeautifulSoup(r_pr.content, "html.parser")

            # Return text of company name. Parse out ticker, market, etc.
            # If NoneType returned (no company title), reasonable to assume no company
            # data on page.
            try:
                company = soup_pr.find("div", {"class": "title"}).text
            except AttributeError:
                continue
            try:
                idx = company.index('(') - 1
                company = company[0:idx]
            except AttributeError:
                pass

            # Parse for time stamp on profile url.
            # For some unknown reason, yfs_market_time tag not found in ~1/500
            # company profiles that were manually confirmed to have that tag.
            try:
                mrkt_time = soup_pr.find("span", {"id":"yfs_market_time"}).text
                idx = mrkt_time.index("EDT") + 3
                mrkt_time = mrkt_time[0:idx]
            except AttributeError:
                mrkt_time = datetime.datetime.now()

            # Dictionary updated with results from all 3 "get" functions.
            # Subsequently passed to row_x_num_execs()
            output_dict = {'Duns': sheet[i][0], 'Street_Ticker': sheet[i][1],
                           'Street_Exchange': sheet[i][2],'Time Stamp': mrkt_time,
                           'Company': company}

            # Workhorse functions calls.
            try:
                output_dict.update(get_profile(soup_pr))
            except TypeError:
                pass
            try:
                output_dict.update(get_details(soup_pr))
            except TypeError:
                pass
            try:
                output_dict.update(get_stock_data(soup_ks))
            except TypeError:
                pass

            # Don't write blank rows (output_dict is initialized with length of 4)
            if len(output_dict) < 5:
                continue

            # Final output object passed to DictWriter -- A list of dictionaries.
            # One dictionary for each key exec
            output_dicts_list = row_x_num_execs(output_dict)

            # TODO: inefficient - consider different approach
            # Make sure headers are identical to fieldnames
            # If not, change fieldname to the header string
            array_of_keys = sorted(output_dict.keys())
            for header in array_of_keys:
                if header not in fieldnames:
                    #print("not in fieldnames")
                    for i in range(len(fieldnames)):
                        if header[0:-3] in fieldnames[i]:
                            #print("header: ", header, ", in fieldnames")
                            fieldnames[i] = header
                            break

            writer = csv.DictWriter(wfile, delimiter=",", fieldnames=fieldnames,
                                    extrasaction='ignore', lineterminator='')
            if write_header_bool:
                writer.writeheader()
                write_header_bool = False
            #print(output_dicts_list)
            for d in output_dicts_list:
                try:
                    writer.writerow(d)
                except TypeError as t:
                    pass
                # A few exec names have funky letters that utf-8 can't encode
                except UnicodeEncodeError as u:
                    for key in d.keys():
                        try:
                            d[key] = d[key].encode(sys.stdout.encoding, errors='replace')
                        except AttributeError:
                            continue
                    writer.writerow(d)
                    pass

if __name__=="__main__":
    yahoo_finance("input.csv", "output.csv")
# Uncomment cProfile and Main()for program speed stats
#cProfile.run("Main()")

